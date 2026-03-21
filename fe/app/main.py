import os
from uuid import uuid4

import requests
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "frontend_secret_key"
API = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 10
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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



def auth_headers():
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}



def require_login():
    if not session.get("token"):
        return redirect(url_for("login"))
    return None



def translate_error_code(code: str | None) -> str | None:
    translations = {
        "username_conflict": "Ese nombre de usuario ya está registrado.",
        "email_conflict": "Ese correo ya está registrado.",
        "invalid_password": "No se pudo procesar la contraseña.",
        "user_conflict": "No se pudo crear el usuario porque ya existe un registro en conflicto.",
        "validation_error": "Hay datos inválidos en el formulario.",
        "http_401": "No tienes autorización para realizar esta acción.",
        "invalid_data": "Hay datos inválidos para completar la operación.",
        "database_conflict": "Hubo un conflicto con la base de datos.",
        "internal_server_error": "Ocurrió un error interno del servidor.",
    }
    return translations.get(code)



def translate_detail(detail: str) -> str:
    translations = {
        "Invalid username or password": "Credenciales inválidas.",
        "Invalid or expired token": "El token es inválido o expiró.",
        "Invalid authentication credentials": "Las credenciales de autenticación no son válidas.",
        "Username is already registered": "Ese nombre de usuario ya está registrado.",
        "Email is already registered": "Ese correo ya está registrado.",
        "Password could not be processed": "No se pudo procesar la contraseña.",
        "User could not be created because it conflicts with an existing record": "No se pudo crear el usuario porque entra en conflicto con un registro existente.",
        "Pet not found": "No se encontró la mascota.",
        "Adoption request could not be created": "No se pudo crear la solicitud de adopción.",
        "Adoption not found or not allowed": "No se encontró la adopción o no tienes permiso para completarla.",
        "Invalid data for the requested operation": "Hay datos inválidos para completar la operación.",
        "Database conflict": "Hubo un conflicto con la base de datos.",
        "Internal server error": "Ocurrió un error interno del servidor.",
        "Validation error": "Hay datos inválidos en el formulario.",
    }
    return translations.get(detail, detail)



def api_detail(response, default_message: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return default_message

    error = payload.get("error") or {}
    code = error.get("code")
    translated = translate_error_code(code)
    if translated:
        return translated

    detail = payload.get("detail")
    if isinstance(detail, str):
        return translate_detail(detail)
    return default_message



def allowed_image_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS



def save_uploaded_pet_image():
    image = request.files.get("photo")
    if image is None or image.filename == "":
        return None, None, "Debes subir una imagen para la mascota."

    if not allowed_image_file(image.filename):
        return None, None, "Solo se permiten archivos .jpg, .jpeg o .png."

    filename = secure_filename(image.filename)
    extension = filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid4().hex}.{extension}"
    destination = os.path.join(UPLOAD_FOLDER, unique_name)
    image.save(destination)
    photo_url = url_for("static", filename=f"uploads/{unique_name}", _external=True)
    return photo_url, destination, None



def request_pet_catalog():
    try:
        response = requests.get(f"{API}/pets/catalog", timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return [], "El servicio de catálogo no está disponible en este momento."

    if response.ok:
        return response.json(), None
    return [], api_detail(response, "No se pudo cargar el catálogo de adopción.")


@app.route("/")
def index():
    return redirect(url_for("login"))


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
            payload = response.json()
            session["token"] = payload.get("access_token")
            session["username"] = username
            flash("Bienvenido de nuevo.", "success")
            return redirect(url_for("dashboard"))

        flash("Credenciales inválidas.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    guard = require_login()
    if guard:
        return guard

    pets = []
    try:
        response = requests.get(
            f"{API}/pets/mine", headers=auth_headers(), timeout=REQUEST_TIMEOUT
        )
        if response.ok:
            pets = response.json()
        else:
            flash(api_detail(response, "No se pudieron cargar tus mascotas."), "error")
    except requests.RequestException:
        flash("El servicio del panel no está disponible.", "error")

    return render_template("dashboard.html", pets=pets)


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
            if saved_path and os.path.exists(saved_path):
                os.remove(saved_path)
            flash("El servicio de mascotas no está disponible.", "error")
            return render_template("add_pet.html")

        if response.status_code == 201:
            flash("Mascota agregada correctamente.", "success")
            return redirect(url_for("dashboard"))

        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)
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
            flash(api_detail(response, "No se pudo actualizar el estado de adopción."), "error")
    except requests.RequestException:
        flash("El servicio de mascotas no está disponible.", "error")

    return redirect(url_for("dashboard"))


@app.route("/catalog")
def catalog():
    guard = require_login()
    if guard:
        return guard

    pets, error = request_pet_catalog()
    if error:
        flash(error, "error")
    return render_template("catalog.html", pets=pets)


@app.route("/adopt/<int:pet_id>", methods=["GET", "POST"])
def adopt(pet_id: int):
    guard = require_login()
    if guard:
        return guard

    pets, error = request_pet_catalog()
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
            return redirect(url_for("catalog"))

        flash(api_detail(response, "No se pudo enviar tu solicitud de adopción."), "error")

    return render_template("adopt.html", pet=pet)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
