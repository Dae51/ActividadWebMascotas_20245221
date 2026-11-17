import logging
import os
import secrets
from uuid import uuid4

import requests
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("pawshome.web")

app = Flask(__name__, template_folder="templates", static_folder="static")

API = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
WS_PUBLIC_URL = os.getenv("WS_PUBLIC_URL", "ws://localhost:8000/ws/notifications")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
DEBUG = os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}

UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
}


def _load_secret_key() -> str:
    secret = os.getenv("SECRET_KEY", "").strip()
    if secret:
        return secret

    logger.warning(
        "SECRET_KEY is not configured. An ephemeral key was generated, so every "
        "browser session will be invalidated when the process restarts."
    )
    return secrets.token_urlsafe(48)


app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "").strip().lower()
    in {"1", "true", "yes", "on"},
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES + 512 * 1024,
)


# --- Presentation helpers -------------------------------------------------


@app.template_filter("status_es")
def status_es(value: str) -> str:
    return {
        "active": "activo",
        "pending": "pendiente",
        "adopted": "adoptado",
        "approved": "aprobado",
        "rejected": "rechazado",
        "completed": "completado",
    }.get(value, value)


@app.template_filter("species_es")
def species_es(value: str) -> str:
    return {
        "dog": "perro",
        "cat": "gato",
        "rabbit": "conejo",
        "bird": "ave",
    }.get((value or "").lower(), value)


@app.template_filter("yesno_es")
def yesno_es(value: bool) -> str:
    return "Sí" if value else "No"


@app.template_filter("datetime_es")
def datetime_es(value: str | None) -> str:
    if not value:
        return "—"
    return str(value).replace("T", " ")[:16]


def csrf_token() -> str:
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


@app.context_processor
def inject_globals() -> dict:
    return {"csrf_token": csrf_token}


@app.before_request
def protect_from_csrf():
    if request.method != "POST":
        return None

    expected = session.get("_csrf", "")
    sent = request.headers.get("X-CSRF-Token") or request.form.get("_csrf", "")
    if expected and sent and secrets.compare_digest(expected, sent):
        return None

    logger.info("Rejected POST without a valid CSRF token: %s", request.path)
    flash("La sesión expiró o el formulario no es válido. Inténtalo de nuevo.", "error")
    return redirect(url_for("dashboard") if session.get("token") else url_for("login"))


@app.errorhandler(413)
def handle_too_large(_):
    flash(f"La imagen supera el límite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.", "error")
    return redirect(url_for("add_pet") if session.get("token") else url_for("login"))


# --- API client -----------------------------------------------------------


def auth_headers() -> dict:
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def require_login():
    if not session.get("token"):
        return redirect(url_for("login"))
    return None


def api_detail(response, default_message: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return default_message

    error = payload.get("error") or {}
    translated = translate_error_code(error.get("code"))
    if translated:
        return translated

    detail = payload.get("detail")
    if isinstance(detail, str):
        return translate_detail(detail)
    return default_message


def translate_error_code(code: str | None) -> str | None:
    translations = {
        "username_conflict": "Ese nombre de usuario ya está registrado.",
        "email_conflict": "Ese correo ya está registrado.",
        "invalid_password": "No se pudo procesar la contraseña.",
        "user_conflict": "No se pudo crear el usuario porque ya existe un registro en conflicto.",
        "validation_error": "Hay datos inválidos en el formulario.",
        "pet_not_found": "No se encontró la mascota.",
        "pet_not_available": "La mascota no está disponible para adopción.",
        "cannot_adopt_own_pet": "No puedes adoptar tu propia mascota.",
        "adoption_request_exists": "Ya tienes una solicitud de adopción activa para esta mascota.",
        "adoption_not_found": "No se encontró la adopción.",
        "adoption_not_pending": "Solo se pueden aprobar solicitudes pendientes.",
        "adoption_not_approved": "Solo se pueden completar adopciones aprobadas.",
        "adoption_not_rejectable": "La solicitud ya no se puede rechazar.",
        "adoption_already_completed": "La adopción ya fue completada.",
        "not_pet_owner": "No tienes permiso para realizar esta acción.",
        "http_401": "No tienes autorización para realizar esta acción. Inicia sesión de nuevo.",
        "http_403": "No tienes permiso para realizar esta acción.",
        "http_404": "No se encontró el recurso solicitado.",
        "http_409": "La operación entra en conflicto con el estado actual del recurso.",
        "invalid_data": "Hay datos inválidos para completar la operación.",
        "database_conflict": "Hubo un conflicto con la base de datos.",
        "database_unavailable": "La base de datos no está disponible en este momento.",
        "internal_server_error": "Ocurrió un error interno del servidor.",
    }
    return translations.get(code)


def translate_detail(detail: str) -> str:
    translations = {
        "Invalid username or password": "Credenciales inválidas.",
        "Invalid or expired token": "El token es inválido o expiró.",
        "Invalid authentication credentials": "Las credenciales de autenticación no son válidas.",
        "Missing authentication credentials": "Debes iniciar sesión para continuar.",
        "Username is already registered": "Ese nombre de usuario ya está registrado.",
        "Email is already registered": "Ese correo ya está registrado.",
        "Password could not be processed": "No se pudo procesar la contraseña.",
        "Pet not found": "No se encontró la mascota.",
        "You cannot adopt your own pet": "No puedes adoptar tu propia mascota.",
        "Pet is not available for adoption": "La mascota no está disponible para adopción.",
        "You already have an active adoption request for this pet": "Ya tienes una solicitud activa para esta mascota.",
        "Adoption not found": "No se encontró la adopción.",
        "Only pending requests can be approved": "Solo se pueden aprobar solicitudes pendientes.",
        "Only approved adoptions can be completed": "Solo se pueden completar adopciones aprobadas.",
        "This adoption can no longer be rejected": "La solicitud ya no se puede rechazar.",
        "Adoption is already completed": "La adopción ya fue completada.",
        "You are not allowed to manage this adoption": "No tienes permiso para gestionar esta adopción.",
        "You are not allowed to modify this pet": "No tienes permiso para modificar esta mascota.",
        "Notification not found": "No se encontró la notificación.",
        "Invalid data for the requested operation": "Hay datos inválidos para completar la operación.",
        "Database conflict": "Hubo un conflicto con la base de datos.",
        "Database is not available": "La base de datos no está disponible en este momento.",
        "Internal server error": "Ocurrió un error interno del servidor.",
        "Validation error": "Hay datos inválidos en el formulario.",
    }
    return translations.get(detail, detail)


def fetch_catalog() -> tuple[list, str | None]:
    try:
        response = requests.get(
            f"{API}/pets/catalog",
            params={"limit": 100},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return [], "El servicio de catálogo no está disponible en este momento."

    if response.ok:
        return response.json(), None
    return [], api_detail(response, "No se pudo cargar el catálogo de adopción.")


def fetch_notifications() -> tuple[list, str | None]:
    try:
        response = requests.get(
            f"{API}/notifications",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return [], "El servicio de notificaciones no está disponible."

    if response.ok:
        return response.json(), None
    return [], api_detail(response, "No se pudieron cargar tus notificaciones.")


# --- Uploads --------------------------------------------------------------


def detect_image_extension(stream) -> str | None:
    header = stream.read(16)
    stream.seek(0)
    for signature, extension in _IMAGE_SIGNATURES.items():
        if header.startswith(signature):
            return extension
    return None


def save_uploaded_pet_image():
    image = request.files.get("photo")
    if image is None or image.filename == "":
        return None, None, "Debes subir una imagen para la mascota."

    extension = detect_image_extension(image.stream)
    if extension is None:
        return None, None, "El archivo no es una imagen JPEG o PNG válida."

    image.stream.seek(0, os.SEEK_END)
    size = image.stream.tell()
    image.stream.seek(0)
    if size > MAX_UPLOAD_BYTES:
        return None, None, "La imagen supera el tamaño máximo permitido."

    unique_name = f"{uuid4().hex}.{extension}"
    destination = os.path.join(UPLOAD_FOLDER, unique_name)
    image.save(destination)
    return f"/static/uploads/{unique_name}", destination, None


def remove_file(path: str | None) -> None:
    if path and os.path.exists(path):
        os.remove(path)


# --- Authentication -------------------------------------------------------


@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("token") else url_for("login"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        payload = {
            "username": request.form.get("username", "").strip(),
            "email": request.form.get("email", "").strip(),
            "password": request.form.get("password", ""),
            "full_name": request.form.get("full_name", "").strip() or None,
        }
        try:
            response = requests.post(
                f"{API}/auth/register", json=payload, timeout=REQUEST_TIMEOUT
            )
        except requests.RequestException:
            flash("El servicio de registro no está disponible.", "error")
            return render_template("register.html")

        if response.status_code == 201:
            flash("Cuenta creada correctamente. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("login"))

        flash(api_detail(response, "No se pudo crear tu cuenta."), "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            response = requests.post(
                f"{API}/auth/login",
                json={"username": username, "password": password},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            flash("El servicio de autenticación no está disponible.", "error")
            return render_template("login.html")

        if response.status_code == 200:
            session.clear()
            session["token"] = response.json().get("access_token")
            session["username"] = username
            csrf_token()
            flash("Bienvenido de nuevo.", "success")
            return redirect(url_for("dashboard"))

        flash("Credenciales inválidas.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- Pets -----------------------------------------------------------------


@app.route("/dashboard")
def dashboard():
    guard = require_login()
    if guard:
        return guard

    pets: list = []
    received: list = []
    requested: list = []

    try:
        pets_response = requests.get(
            f"{API}/pets/mine", headers=auth_headers(), timeout=REQUEST_TIMEOUT
        )
        if pets_response.ok:
            pets = pets_response.json()
        else:
            flash(
                api_detail(pets_response, "No se pudieron cargar tus mascotas."),
                "error",
            )
    except requests.RequestException:
        flash("El servicio del panel no está disponible.", "error")

    try:
        received_response = requests.get(
            f"{API}/adoptions/received", headers=auth_headers(), timeout=REQUEST_TIMEOUT
        )
        if received_response.ok:
            received = received_response.json()
    except requests.RequestException:
        pass

    try:
        requested_response = requests.get(
            f"{API}/adoptions/mine", headers=auth_headers(), timeout=REQUEST_TIMEOUT
        )
        if requested_response.ok:
            requested = requested_response.json()
    except requests.RequestException:
        pass

    return render_template(
        "dashboard.html",
        pets=pets,
        received=received,
        requested=requested,
    )


@app.route("/my-pets/add", methods=["GET", "POST"])
def add_pet():
    guard = require_login()
    if guard:
        return guard

    if request.method == "POST":
        photo_url, saved_path, image_error = save_uploaded_pet_image()
        if image_error:
            flash(image_error, "error")
            return render_template("add_pet.html")

        age_years = request.form.get("age_years", "").strip()
        payload = {
            "name": request.form.get("name", "").strip(),
            "species": request.form.get("species", "").strip(),
            "breed": request.form.get("breed", "").strip() or None,
            "age_years": age_years or None,
            "description": request.form.get("description", "").strip() or None,
            "photo_url": photo_url,
            "is_for_adoption": request.form.get("is_for_adoption") == "on",
        }
        try:
            response = requests.post(
                f"{API}/pets/",
                json=payload,
                headers=auth_headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            remove_file(saved_path)
            flash("El servicio de mascotas no está disponible.", "error")
            return render_template("add_pet.html")

        if response.status_code == 201:
            flash("Mascota agregada correctamente.", "success")
            return redirect(url_for("dashboard"))

        remove_file(saved_path)
        flash(api_detail(response, "No se pudo agregar la mascota."), "error")

    return render_template("add_pet.html")


@app.post("/my-pets/<int:pet_id>/toggle-adoption")
def toggle_adoption(pet_id: int):
    guard = require_login()
    if guard:
        return guard

    current_state = request.form.get("current_state", "false").lower() == "true"
    next_state = not current_state
    try:
        response = requests.patch(
            f"{API}/pets/{pet_id}",
            json={"is_for_adoption": next_state},
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.ok:
            flash(
                "La mascota ahora aparece en el catálogo de adopción."
                if next_state
                else "La mascota fue retirada del catálogo de adopción.",
                "success",
            )
        else:
            flash(
                api_detail(response, "No se pudo actualizar el estado de adopción."),
                "error",
            )
    except requests.RequestException:
        flash("El servicio de mascotas no está disponible.", "error")

    return redirect(url_for("dashboard"))


@app.post("/my-pets/<int:pet_id>/delete")
def delete_pet(pet_id: int):
    guard = require_login()
    if guard:
        return guard

    try:
        response = requests.delete(
            f"{API}/pets/{pet_id}", headers=auth_headers(), timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 204:
            flash("La mascota fue eliminada.", "success")
        else:
            flash(api_detail(response, "No se pudo eliminar la mascota."), "error")
    except requests.RequestException:
        flash("El servicio de mascotas no está disponible.", "error")

    return redirect(url_for("dashboard"))


# --- Catalog & adoption ---------------------------------------------------


@app.route("/catalog")
def catalog():
    guard = require_login()
    if guard:
        return guard

    pets, error = fetch_catalog()
    if error:
        flash(error, "error")
    return render_template("catalog.html", pets=pets)


@app.route("/adopt/<int:pet_id>", methods=["GET", "POST"])
def adopt(pet_id: int):
    guard = require_login()
    if guard:
        return guard

    pets, error = fetch_catalog()
    pet = next((item for item in pets if item.get("id") == pet_id), None)
    if pet is None:
        if error:
            flash(error, "error")
        else:
            flash("Esa mascota ya no está disponible para adopción.", "error")
        return redirect(url_for("catalog"))

    if request.method == "POST":
        payload = {
            "pet_id": pet_id,
            "message": request.form.get("message", "").strip() or None,
        }
        try:
            response = requests.post(
                f"{API}/adoptions/request",
                json=payload,
                headers=auth_headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            flash("El servicio de adopciones no está disponible.", "error")
            return render_template("adopt.html", pet=pet)

        if response.status_code == 201:
            flash("Solicitud de adopción enviada correctamente.", "success")
            return redirect(url_for("dashboard"))

        flash(
            api_detail(response, "No se pudo enviar tu solicitud de adopción."),
            "error",
        )

    return render_template("adopt.html", pet=pet)


ADOPTION_ACTIONS = {
    "approve": "Solicitud aprobada.",
    "reject": "Solicitud rechazada.",
    "complete": "Adopción completada: la mascota cambió de dueño.",
}


@app.post("/adoptions/<int:adoption_id>/<action>")
def manage_adoption(adoption_id: int, action: str):
    guard = require_login()
    if guard:
        return guard

    if action not in ADOPTION_ACTIONS:
        abort(404)

    try:
        response = requests.post(
            f"{API}/adoptions/{adoption_id}/{action}",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.ok:
            flash(ADOPTION_ACTIONS[action], "success")
        else:
            flash(
                api_detail(response, "No se pudo actualizar la solicitud."),
                "error",
            )
    except requests.RequestException:
        flash("El servicio de adopciones no está disponible.", "error")

    return redirect(url_for("dashboard"))


# --- Notifications --------------------------------------------------------


@app.get("/notifications")
def notifications():
    guard = require_login()
    if guard:
        return guard

    items, error = fetch_notifications()
    if error:
        flash(error, "error")
    return render_template("notifications.html", notifications=items)


@app.post("/notifications/<int:notification_id>/read")
def notification_read(notification_id: int):
    guard = require_login()
    if guard:
        return guard

    try:
        response = requests.post(
            f"{API}/notifications/{notification_id}/read",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.ok:
            flash("Aviso marcado como leído.", "success")
        else:
            flash(api_detail(response, "No se pudo marcar el aviso."), "error")
    except requests.RequestException:
        flash("El servicio de notificaciones no está disponible.", "error")

    return redirect(url_for("notifications"))


@app.post("/notifications/read-all")
def notifications_read_all():
    guard = require_login()
    if guard:
        return guard

    try:
        response = requests.post(
            f"{API}/notifications/read-all",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.ok:
            flash("Todos los avisos fueron marcados como leídos.", "success")
        else:
            flash(api_detail(response, "No se pudieron marcar los avisos."), "error")
    except requests.RequestException:
        flash("El servicio de notificaciones no está disponible.", "error")

    return redirect(url_for("notifications"))


@app.get("/api/notifications")
def api_notifications():
    if not session.get("token"):
        return jsonify({"items": [], "unread": 0}), 401

    try:
        response = requests.get(
            f"{API}/notifications",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return jsonify({"items": [], "unread": 0}), 503

    if not response.ok:
        return jsonify({"items": [], "unread": 0}), response.status_code

    items = response.json()
    unread = sum(1 for item in items if not item.get("is_read"))
    return jsonify({"items": items, "unread": unread})


@app.post("/api/notifications/read-all")
def api_read_all():
    if not session.get("token"):
        return jsonify({"ok": False}), 401

    try:
        response = requests.post(
            f"{API}/notifications/read-all",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return jsonify({"ok": False}), 503

    return jsonify({"ok": response.ok}), (200 if response.ok else 502)


@app.get("/api/ws-ticket")
def api_ws_ticket():
    if not session.get("token"):
        return jsonify({"error": "unauthorized"}), 401

    try:
        response = requests.post(
            f"{API}/auth/ws-ticket",
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return jsonify({"error": "unavailable"}), 503

    if not response.ok:
        return jsonify({"error": "unauthorized"}), response.status_code

    return jsonify({"ticket": response.json()["ticket"], "url": WS_PUBLIC_URL})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
