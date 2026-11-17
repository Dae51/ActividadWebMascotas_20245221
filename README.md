# PawsHome

Plataforma web para la gestión de mascotas y el proceso de adopción responsable. El sistema permite a un usuario registrar sus mascotas, publicarlas en un catálogo público de adopción, recibir y resolver solicitudes de otros usuarios, y completar la transferencia de propiedad de forma controlada y trazable.

El proyecto está compuesto por dos servicios aplicativos independientes (API + interfaz web) y una base de datos PostgreSQL, orquestados con Docker Compose.

| Campo | Valor |
| --- | --- |
| Nombre del proyecto | PawsHome |
| Tipo | Aplicación web de tres capas |
| Dominio | Veterinaria / cuidado de mascotas / adopción |
| Arquitectura | Cliente ligero + API REST + base de datos relacional |
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic |
| Frontend | Python 3.11 · Flask · Jinja2 · CSS3 · JavaScript (mejora progresiva) |
| Base de datos | PostgreSQL 18 |
| Orquestación | Docker Compose |
| Idioma de la interfaz | Español |
| Estado | Funcional, endurecido y con pruebas automatizadas |

---

## Tabla de contenidos

1. [Visión general](#visión-general)
2. [Características principales](#características-principales)
3. [Stack tecnológico](#stack-tecnológico)
4. [Arquitectura del sistema](#arquitectura-del-sistema)
5. [Estructura del repositorio](#estructura-del-repositorio)
6. [Modelo de datos](#modelo-de-datos)
7. [Migraciones de base de datos](#migraciones-de-base-de-datos)
8. [Referencia de la API](#referencia-de-la-api)
9. [Canal en tiempo real (WebSocket)](#canal-en-tiempo-real-websocket)
10. [Capa de presentación (frontend)](#capa-de-presentación-frontend)
11. [Seguridad](#seguridad)
12. [Puesta en marcha](#puesta-en-marcha)
13. [Variables de entorno](#variables-de-entorno)
14. [Pruebas y calidad](#pruebas-y-calidad)
15. [Guía de usuario](#guía-de-usuario)
16. [Flujo funcional de una adopción](#flujo-funcional-de-una-adopción)
17. [Decisiones de diseño](#decisiones-de-diseño)
18. [Pendientes conscientes](#pendientes-conscientes)
19. [Solución de problemas](#solución-de-problemas)
20. [Glosario](#glosario)

---

## Visión general

PawsHome resuelve un problema acotado: **poner en contacto a quien debe entregar una mascota con quien desea adoptarla, dejando trazabilidad completa del proceso**.

El sistema se organiza en dos roles implícitos que comparten el mismo tipo de cuenta:

- **Dueño / cuidador**: registra mascotas, decide cuáles se publican en el catálogo, aprueba o rechaza solicitudes y completa la adopción.
- **Adoptante**: explora el catálogo, envía solicitudes y sigue el estado de cada una.

Ambos roles conviven en la entidad `users`. Un usuario puede ser dueño de unas mascotas y adoptante de otras al mismo tiempo; las validaciones del dominio impiden que un usuario adopte su propia mascota.

### Principios de diseño

- **Separación estricta de responsabilidades** en el backend: `router → service → repository → model`.
- **Transacciones explícitas**: los repositorios solo hacen `flush`; los servicios delimitan la unidad de trabajo con `transaction()` y confirman una sola vez.
- **El frontend nunca accede a la base de datos**: toda lectura/escritura pasa por la API REST.
- **Contrato de errores uniforme** con códigos de máquina (`code`) que el frontend traduce a mensajes en español.
- **Sesión de navegador delgada**: el frontend solo conserva el token JWT en su cookie de sesión firmada; la autorización real vive en la API.
- **Interfaz renderizada en servidor** (SSR) sin framework JavaScript; el único script del cliente es una mejora progresiva para notificaciones en tiempo real.
- **Configuración por entorno**: ningún secreto real vive en el código ni en el repositorio.

---

## Características principales

### Autenticación y cuentas
- Registro con validación de unicidad de `username` y `email`.
- Política mínima de credenciales: usuario de 3–50 caracteres alfanuméricos (`_ . -` permitidos) y contraseña de 8–128 caracteres.
- Hashing con `bcrypt_sha256` (compatible con hashes `bcrypt` heredados).
- JWT (HS256) con expiración configurable.
- Rutas protegidas con `HTTPBearer`; ausencia de credenciales devuelve `401` con `WWW-Authenticate: Bearer`.
- Credenciales de WebSocket separadas del token de acceso mediante *tickets* de corta vida y alcance restringido.

### Gestión de mascotas
- Alta con nombre, especie (catálogo cerrado), raza, edad, descripción y fotografía.
- Validación de imagen por **firma binaria real** (JPEG/PNG), no por extensión.
- Límite de tamaño configurable (`MAX_UPLOAD_MB`, 5 MB por defecto) aplicado en dos capas.
- Renombrado con UUID y almacenamiento con ruta relativa (`/static/uploads/...`).
- Edición parcial real: un campo opcional puede vaciarse enviando `null`.
- Eliminación por el propietario.
- Aislamiento por propietario: `403` al intentar modificar recursos ajenos, `404` si no existen.
- Publicación / retiro del catálogo con un interruptor desde el panel.

### Catálogo y adopción
- Catálogo paginado que expone únicamente mascotas publicadas y activas.
- Solicitud con mensaje para el dueño.
- Reglas de negocio: no adoptar la propia mascota, no duplicar solicitudes activas, no solicitar mascotas no publicadas.
- Flujo completo de estados: `pending → approved → completed`, con `rejected` como salida alternativa.
- Validación estricta de transiciones: no se puede completar una adopción que no esté aprobada.
- Cierre atómico: adopción completada + transferencia de propiedad + rechazo de las solicitudes rivales + notificaciones, todo en una sola transacción.
- Vista del dueño (solicitudes recibidas) y del adoptante (solicitudes enviadas).

### Notificaciones
- Persistencia de eventos en `notifications`.
- Bandeja de avisos con marcado individual y masivo.
- Contador de no leídos con insignia en la navegación.
- Entrega en tiempo real por WebSocket, programada en el bucle de eventos correcto para que funcione desde handlers HTTP en hilos de trabajo.
- Reconexión automática en el cliente.

### Presentación
- Interfaz en español, responsiva, con sistema de tokens CSS.
- Mensajes flash categorizados y traducción de errores de la API.
- Confirmación antes de acciones destructivas.

---

## Stack tecnológico

### Backend — API

| Tecnología | Versión | Rol |
| --- | --- | --- |
| Python | 3.11 (imagen `python:3.11-slim`) | Lenguaje de ejecución |
| FastAPI | 0.110.0 | Framework HTTP, validación y OpenAPI |
| Uvicorn | 0.29.0 (`[standard]`) | Servidor ASGI |
| SQLAlchemy | 2.0.29 | ORM con tipado (`Mapped`, `mapped_column`) |
| Alembic | 1.13.1 | Migraciones versionadas del esquema |
| psycopg2-binary | 2.9.9 | Driver PostgreSQL |
| Pydantic | 2.7.0 (`[email]`) | Esquemas y validación |
| python-jose | 3.3.0 (`[cryptography]`) | Firma y verificación JWT |
| passlib | 1.7.4 (`[bcrypt]`) | Contexto de hashing |
| bcrypt | 4.0.1 | Algoritmo de hashing |
| websockets | 12.0 | Canal en tiempo real |

### Frontend — Interfaz web

| Tecnología | Versión | Rol |
| --- | --- | --- |
| Python | 3.11 (imagen `python:3.11-slim`) | Lenguaje de ejecución |
| Flask | 3.0.3 | Framework web y enrutamiento |
| Jinja2 | (incluido en Flask) | Motor de plantillas SSR |
| requests | 2.31.0 | Cliente HTTP hacia la API |
| Werkzeug | (incluido en Flask) | Sesiones firmadas |
| CSS3 | — | Hoja de estilos propia, sin framework |
| JavaScript (ES2020) | — | Único script cliente: notificaciones en vivo |

### Calidad

| Herramienta | Rol |
| --- | --- |
| pytest 8.2 + httpx | Pruebas de API (SQLite en memoria, sin dependencia de PostgreSQL) |
| ruff 0.4 | Linter (reglas `E9` y `F`) |
| GitHub Actions | CI: lint + pruebas en cada push y PR |

### Infraestructura

| Componente | Versión | Rol |
| --- | --- | --- |
| PostgreSQL | 18 (`postgres:18`) | Base de datos relacional |
| Docker / Compose | — | Empaquetado y orquestación de tres servicios |

---

## Arquitectura del sistema

### Vista de despliegue

```mermaid
graph TB
    subgraph Host["Host Docker"]
        Browser["Navegador del usuario"]

        subgraph FE["Contenedor fe · Flask :5000"]
            FEApp["app/main.py<br/>Rutas · CSRF · proxy API"]
            FEStatic["/static<br/>style.css · notifications.js · uploads (volumen)"]
        end

        subgraph BE["Contenedor be · FastAPI :8000"]
            Router["Routers<br/>auth · pets · adoptions · notifications · ws"]
            Service["Services<br/>Reglas de negocio · transacciones"]
            Repo["Repositories<br/>flush (sin commit)"]
            ORM["Modelos SQLAlchemy"]
        end

        subgraph DB["Contenedor db · PostgreSQL :5432"]
            Schema["Esquema gestionado por Alembic"]
        end
    end

    Browser -->|"HTTP :5000<br/>formularios HTML"| FEApp
    Browser -->|"HTTP :5000"| FEStatic
    FEApp -->|"requests · JSON<br/>Bearer token"| Router
    Browser -.->|"WebSocket :8000<br/>handshake por ticket"| Router
    Router --> Service
    Service --> Repo
    Repo --> ORM
    ORM -->|"psycopg2"| Schema
```

### Capas del backend

| Capa | Directorio | Responsabilidad | Regla de dependencia |
| --- | --- | --- | --- |
| **Transporte** | `app/routers/` | Endpoints, dependencias, delimitación de transacción | Depende de `services` y `schemas` |
| **Aplicación** | `app/services/` | Reglas de negocio, transiciones de estado, atomicidad | Depende de `repositories` y `models` |
| **Persistencia** | `app/repositories/` | Consultas y `flush`; nunca confirman | Depende solo de `models` |
| **Dominio** | `app/models/` | Entidades y mapeo ORM | No depende de capas superiores |
| **Contratos** | `app/schemas/` | Validación de entrada y serialización | Depende de `models` (enums) |

### Unidad de trabajo

```mermaid
sequenceDiagram
    autonumber
    participant R as Router
    participant S as Service
    participant P as Repository
    participant D as PostgreSQL

    R->>S: complete_adoption(db, id, owner)
    S->>S: valida estado == approved
    S->>D: BEGIN
    S->>P: complete(adoption)
    P->>D: UPDATE adoptions (flush)
    S->>P: transfer_ownership(pet, adopter)
    P->>D: UPDATE pets (flush)
    S->>P: set_status(otras solicitudes, rejected)
    S->>P: send(notificaciones)
    S->>D: COMMIT
    S-->>R: adopción completada
    S->>S: publish() a los WebSocket conectados
```

Ningún repositorio llama a `commit()`. El servicio abre `transaction(db)`, compone todas las escrituras y confirma una sola vez; si algo falla, `rollback` revierte el conjunto completo. La publicación por WebSocket ocurre **después** del commit, de modo que nunca se anuncia un evento que la base de datos no conservó.

### Ciclo de vida de una petición HTTP

1. El navegador envía un formulario a Flask con el token CSRF.
2. Flask valida la sesión y el token CSRF (`before_request`).
3. Flask llama a la API con `Authorization: Bearer <jwt>`.
4. FastAPI resuelve `get_current_user`, ejecuta el servicio y confirma la transacción.
5. Flask recibe el JSON, traduce errores si corresponde y renderiza la plantilla.

### Comunicación entre servicios

- El frontend consume la API **del lado del servidor**; el navegador nunca ve el JWT.
- Timeout configurable (`REQUEST_TIMEOUT_SECONDS`, 10 s por defecto).
- `API_BASE_URL` resuelve `http://be:8000` por DNS interno de Compose.
- CORS queda restringido a orígenes explícitos y configurable (`CORS_ORIGINS`).

---

## Estructura del repositorio

```
ActividadWebMascotas_20245221/
├── compose.yml                     # Orquestación de db, be y fe
├── .env.example                    # Plantilla de configuración (copiar a .env)
├── .gitignore                      # Excluye secretos, cachés y artefactos
├── pyproject.toml                  # Configuración de ruff y pytest
├── README.md                       # Este documento
│
├── .github/workflows/ci.yml        # Integración continua: lint + tests
│
├── be/                             # Backend · API REST (FastAPI)
│   ├── Dockerfile                  # Imagen python:3.11-slim
│   ├── docker-entrypoint.sh        # alembic upgrade head + uvicorn
│   ├── alembic.ini                 # Configuración de migraciones
│   ├── requirements.txt            # Dependencias de ejecución
│   ├── requirements-dev.txt        # + pytest, httpx, ruff
│   ├── migrations/
│   │   ├── env.py                  # Entorno Alembic (lee DATABASE_URL)
│   │   ├── script.py.mako
│   │   └── versions/0001_initial.py# Esquema inicial completo
│   ├── tests/
│   │   ├── conftest.py             # Cliente con SQLite en memoria
│   │   └── test_api.py             # 16 pruebas de API
│   └── app/
│       ├── main.py                 # App, CORS, manejadores de error, health
│       ├── config.py               # Settings inmutables desde entorno
│       ├── database.py             # Engine, sesión, Base, transaction()
│       ├── errors.py               # Excepción de dominio ApiError
│       ├── models/                 # Entidades ORM
│       │   ├── user.py
│       │   ├── pet.py
│       │   ├── adoption.py
│       │   └── notification.py
│       ├── schemas/                # Contratos Pydantic
│       │   ├── user.py  pet.py  adoption.py  notification.py  token.py
│       ├── repositories/           # Acceso a datos (solo flush)
│       │   ├── user_repo.py  pet_repo.py
│       │   ├── adoption_repo.py  notification_repo.py
│       ├── services/               # Reglas de negocio
│       │   ├── auth_service.py
│       │   ├── pet_service.py
│       │   ├── adoption_service.py
│       │   └── notification_service.py
│       └── routers/
│           ├── auth.py  pets.py  adoptions.py
│           ├── notifications.py  ws.py  deps.py
│
└── fe/                             # Frontend · Interfaz web (Flask + Jinja2)
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py                 # Rutas, CSRF, uploads, proxy, traducciones
        ├── static/
        │   ├── style.css           # Sistema visual completo
        │   ├── notifications.js    # WebSocket + insignia + avisos emergentes
        │   └── uploads/            # Imágenes (volumen persistente en Compose)
        └── templates/
            ├── base.html      login.html     register.html
            ├── dashboard.html add_pet.html   catalog.html
            ├── adopt.html     notifications.html
```

### Volumetría aproximada

| Componente | Líneas |
| --- | --- |
| API (`be/app`) | ~1 400 |
| Migraciones y tests | ~600 |
| Interfaz (`fe/app` Python + HTML) | ~1 100 |
| Estilos + JavaScript | ~650 |

---

## Modelo de datos

### Diagrama entidad-relación

```mermaid
erDiagram
    USERS ||--o{ PETS : "posee"
    USERS ||--o{ ADOPTIONS : "solicita (adopter_id)"
    USERS ||--o{ ADOPTIONS : "cedía (previous_owner_id)"
    USERS ||--o{ NOTIFICATIONS : "recibe"
    PETS ||--o{ ADOPTIONS : "es objeto de"
    PETS ||--o{ NOTIFICATIONS : "se relaciona con"

    USERS {
        int id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        varchar full_name
        timestamp created_at
        timestamp updated_at
    }

    PETS {
        int id PK
        int owner_id FK
        varchar name
        varchar species
        varchar breed
        numeric age_years
        text description
        varchar photo_url
        boolean is_for_adoption
        petstatus status
        timestamp created_at
        timestamp updated_at
    }

    ADOPTIONS {
        int id PK
        int pet_id FK
        int adopter_id FK
        int previous_owner_id FK
        adoptionstatus status
        text message
        timestamp requested_at
        timestamp completed_at
    }

    NOTIFICATIONS {
        int id PK
        int user_id FK
        varchar title
        text message
        notificationtype type
        boolean is_read
        int related_pet_id FK
        timestamp created_at
    }
```

### Dominio de tablas

#### `users`

| Columna | Tipo | Restricciones | Descripción |
| --- | --- | --- | --- |
| `id` | `INTEGER` | PK, `IDENTITY` | Identificador |
| `username` | `VARCHAR(50)` | `NOT NULL`, `UNIQUE` | Nombre de usuario para login |
| `email` | `VARCHAR(100)` | `NOT NULL`, `UNIQUE` | Correo normalizado a minúsculas |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Hash `bcrypt_sha256` |
| `full_name` | `VARCHAR(100)` | `NULL` | Nombre visible |
| `created_at` / `updated_at` | `TIMESTAMP` | `NOT NULL DEFAULT now()` | Auditoría |

#### `pets`

| Columna | Tipo | Restricciones | Descripción |
| --- | --- | --- | --- |
| `id` | `INTEGER` | PK | Identificador |
| `owner_id` | `INTEGER` | FK → `users.id`, `ON DELETE CASCADE` | Propietario actual |
| `name` | `VARCHAR(100)` | `NOT NULL` | Nombre |
| `species` | `VARCHAR(50)` | `NOT NULL` | Especie (`dog`, `cat`, `rabbit`, `bird`) |
| `breed` | `VARCHAR(100)` | `NULL` | Raza |
| `age_years` | `NUMERIC(4,1)` | `NULL` | Edad con un decimal, 0–100 |
| `description` | `TEXT` | `NULL` | Personalidad, salud, hábitos |
| `photo_url` | `VARCHAR(500)` | `NULL` | Ruta relativa de la imagen |
| `is_for_adoption` | `BOOLEAN` | `NOT NULL DEFAULT false` | Visibilidad en catálogo |
| `status` | `petstatus` | `NOT NULL DEFAULT 'active'` | Ciclo de vida |
| `created_at` / `updated_at` | `TIMESTAMP` | `NOT NULL` | Auditoría |

#### `adoptions`

| Columna | Tipo | Restricciones | Descripción |
| --- | --- | --- | --- |
| `id` | `INTEGER` | PK | Identificador |
| `pet_id` | `INTEGER` | FK → `pets.id`, `CASCADE` | Mascota solicitada |
| `adopter_id` | `INTEGER` | FK → `users.id`, `CASCADE` | Solicitante |
| `previous_owner_id` | `INTEGER` | FK → `users.id`, `CASCADE` | Dueño al momento de solicitar |
| `status` | `adoptionstatus` | `NOT NULL DEFAULT 'pending'` | Estado del proceso |
| `message` | `TEXT` | `NULL` | Mensaje del adoptante |
| `requested_at` | `TIMESTAMP` | `NOT NULL DEFAULT now()` | Fecha de solicitud |
| `completed_at` | `TIMESTAMP` | `NULL` | Fecha de cierre |

`previous_owner_id` es una **instantánea histórica**: conserva quién entregó la mascota aunque `pets.owner_id` cambie tras la adopción.

#### `notifications`

| Columna | Tipo | Restricciones | Descripción |
| --- | --- | --- | --- |
| `id` | `INTEGER` | PK | Identificador |
| `user_id` | `INTEGER` | FK → `users.id`, `CASCADE` | Destinatario |
| `title` | `VARCHAR(255)` | `NOT NULL` | Título corto |
| `message` | `TEXT` | `NOT NULL` | Cuerpo del aviso |
| `type` | `notificationtype` | `NOT NULL DEFAULT 'general'` | Categoría del evento |
| `is_read` | `BOOLEAN` | `NOT NULL DEFAULT false` | Indicador de lectura |
| `related_pet_id` | `INTEGER` | FK → `pets.id`, `SET NULL` | Mascota implicada |
| `created_at` | `TIMESTAMP` | `NOT NULL DEFAULT now()` | Fecha de emisión |

### Enumeraciones

| Enum | Valores | Uso |
| --- | --- | --- |
| `petstatus` | `active`, `pending`, `adopted` | `active` en alta; `pending` al aprobar una solicitud; `adopted` al transferir |
| `adoptionstatus` | `pending`, `approved`, `rejected`, `completed` | Ciclo completo implementado |
| `notificationtype` | `adoption_request`, `adoption_approved`, `adoption_rejected`, `adoption_completed`, `general` | Todos los eventos del flujo |

### Integridad

- **Claves foráneas con cascada**: eliminar un usuario elimina sus mascotas, solicitudes y notificaciones.
- **`ON DELETE SET NULL`** en `notifications.related_pet_id`: el aviso sobrevive a la eliminación de la mascota.
- **`updated_at`** se mantiene con `onupdate=func.now()` en SQLAlchemy, un único mecanismo (ya no hay triggers duplicados).
- **Índices**: `idx_pets_owner`, `idx_pets_adoption`, `idx_adoptions_pet`, `idx_adoptions_adopter`, `idx_notif_user_unread`.

---

## Migraciones de base de datos

El esquema es **propiedad de Alembic**. Ya no existe un `schema.sql` aplicado por el entrypoint de PostgreSQL: la API ejecuta `alembic upgrade head` antes de arrancar y luego inicia Uvicorn.

```bash
# Aplicar migraciones (dentro del contenedor)
docker compose exec be alembic upgrade head

# Crear una migración a partir de los cambios en los modelos
docker compose exec be alembic revision --autogenerate -m "describe el cambio"

# Revisar/editar el archivo generado en be/migrations/versions/ y aplicarlo
docker compose exec be alembic upgrade head

# Revertir la última migración
docker compose exec be alembic downgrade -1

# Historial
docker compose exec be alembic history --verbose
```

La migración `0001_initial` crea los tres tipos enumerados, las cuatro tablas, las claves foráneas y los índices. Su `downgrade` elimina tablas y tipos, por lo que el ciclo completo es reversible (verificado sobre PostgreSQL 18).

---

## Referencia de la API

- **URL base (Compose):** `http://be:8000` (interno) · `http://localhost:8000` (host)
- **Documentación interactiva:** `http://localhost:8000/docs` y `/redoc`
- **Autenticación:** `Authorization: Bearer <access_token>`

### Formato de error uniforme

```json
{
  "detail": "Human readable message",
  "error": {
    "code": "adoption_not_approved",
    "message": "Human readable message",
    "errors": []
  }
}
```

`error.errors` solo aparece en errores de validación (`422`).

### Códigos de error

| Código | HTTP | Significado |
| --- | --- | --- |
| `username_conflict` | 409 | El nombre de usuario ya existe |
| `email_conflict` | 409 | El correo ya está registrado |
| `user_conflict` | 409 | Conflicto de integridad al crear la cuenta |
| `invalid_password` | 400 | La contraseña no se pudo procesar |
| `validation_error` | 422 | Cuerpo inválido (Pydantic) |
| `pet_not_found` | 404 | La mascota no existe |
| `pet_not_available` | 409 | No está publicada o no está activa |
| `cannot_adopt_own_pet` | 400 | Intento de adoptar la propia mascota |
| `adoption_request_exists` | 409 | Ya hay una solicitud activa del mismo usuario |
| `adoption_not_found` | 404 | La adopción no existe |
| `adoption_not_pending` | 409 | Solo se aprueban solicitudes pendientes |
| `adoption_not_approved` | 409 | Solo se completan adopciones aprobadas |
| `adoption_not_rejectable` | 409 | La solicitud ya no se puede rechazar |
| `adoption_already_completed` | 409 | Ya fue completada |
| `not_pet_owner` | 403 | Sin permiso sobre el recurso |
| `database_unavailable` | 503 | Base de datos inaccesible |
| `internal_server_error` | 500 | Error no controlado |

### Endpoints

#### Sistema

| Método | Ruta | Auth | Descripción |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Comprueba la conexión a la base y devuelve `{"status":"ok","version":"1.0.0"}` |

#### Autenticación

| Método | Ruta | Auth | Código | Descripción |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/register` | No | `201` | Crea una cuenta |
| `POST` | `/auth/login` | No | `200` | Devuelve un JWT |
| `POST` | `/auth/ws-ticket` | Sí | `200` | Ticket efímero para el WebSocket |

**`POST /auth/register`**

```json
{
  "username": "alexr",
  "email": "alex@example.com",
  "password": "unaClaveSegura",
  "full_name": "Alex Rivera"
}
```

Restricciones: `username` de 3–50 con `[A-Za-z0-9_.-]`; `password` de 8–128.

**`POST /auth/login`** → `{ "access_token": "…", "token_type": "bearer" }`

**`POST /auth/ws-ticket`** → `{ "ticket": "…", "expires_in": 60 }`

> El ticket lleva `scope="ws"` y `decode_token` lo rechaza como token de acceso, por lo que no puede usarse para llamar a la API.

#### Mascotas

| Método | Ruta | Auth | Código | Descripción |
| --- | --- | --- | --- | --- |
| `GET` | `/pets/catalog?limit=&offset=` | No | `200` | Catálogo paginado (limit 1–100, por defecto 50) |
| `GET` | `/pets/mine` | Sí | `200` | Mascotas del usuario |
| `GET` | `/pets/{pet_id}` | Sí | `200` | Detalle de una mascota |
| `POST` | `/pets/` | Sí | `201` | Registra una mascota |
| `PATCH` | `/pets/{pet_id}` | Sí | `200` | Actualiza campos parciales (`null` limpia opcionales) |
| `DELETE` | `/pets/{pet_id}` | Sí | `204` | Elimina una mascota propia |

**`POST /pets/`**

```json
{
  "name": "Luna",
  "species": "dog",
  "breed": "Mestiza",
  "age_years": 3.5,
  "description": "Tranquila, sociable y entrenada.",
  "photo_url": "/static/uploads/1a2b3c.jpg",
  "is_for_adoption": true
}
```

`species` acepta exactamente `dog`, `cat`, `rabbit` o `bird`; cualquier otro valor devuelve `422`.

#### Adopciones

| Método | Ruta | Auth | Código | Descripción |
| --- | --- | --- | --- | --- |
| `GET` | `/adoptions/received` | Sí | `200` | Solicitudes recibidas por el dueño |
| `GET` | `/adoptions/mine` | Sí | `200` | Solicitudes enviadas por el adoptante |
| `POST` | `/adoptions/request` | Sí | `201` | Crea una solicitud |
| `POST` | `/adoptions/{id}/approve` | Sí | `200` | Pendiente → aprobada |
| `POST` | `/adoptions/{id}/reject` | Sí | `200` | Pendiente/aprobada → rechazada |
| `POST` | `/adoptions/{id}/complete` | Sí | `200` | Aprobada → completada |

`GET /adoptions/received` y `/mine` devuelven objetos enriquecidos:

```json
[
  {
    "id": 4,
    "pet_id": 12,
    "adopter_id": 3,
    "previous_owner_id": 1,
    "status": "pending",
    "message": "Tengo jardín y experiencia con perros.",
    "requested_at": "2026-11-17T15:45:00",
    "completed_at": null,
    "pet": { "id": 12, "name": "Luna", "species": "dog", "photo_url": "/static/uploads/…" },
    "adopter": { "id": 3, "username": "adopter", "full_name": "Adopter" }
  }
]
```

Efectos de cada transición:

| Acción | Adopción | Mascota | Notificación |
| --- | --- | --- | --- |
| `request` | crea `pending` | sin cambios | `adoption_request` al dueño |
| `approve` | `approved` | `status = pending` (sale del catálogo) | `adoption_approved` al adoptante |
| `reject` | `rejected` | vuelve a `active` si no queda otra aprobada | `adoption_rejected` al adoptante |
| `complete` | `completed` + `completed_at` | `owner_id = adopter_id`, `status = adopted`, fuera del catálogo | `adoption_completed` al adoptante y `adoption_rejected` a los rivales |

#### Notificaciones

| Método | Ruta | Auth | Código | Descripción |
| --- | --- | --- | --- | --- |
| `GET` | `/notifications` | Sí | `200` | Últimos 100 avisos, más recientes primero |
| `GET` | `/notifications/unread-count` | Sí | `200` | `{ "unread": 3 }` |
| `POST` | `/notifications/{id}/read` | Sí | `200` | Marca uno como leído (404 si es de otro usuario) |
| `POST` | `/notifications/read-all` | Sí | `200` | Marca todos como leídos |

---

## Canal en tiempo real (WebSocket)

**Endpoint:** `ws://localhost:8000/ws/notifications`

### Handshake por ticket

El token de acceso **no viaja en la URL**. El navegador sigue este protocolo:

```mermaid
sequenceDiagram
    participant J as notifications.js
    participant F as Flask
    participant A as FastAPI
    participant W as WebSocket

    J->>F: GET /api/ws-ticket
    F->>A: POST /auth/ws-ticket (Bearer)
    A-->>F: ticket (scope=ws, 60 s)
    F-->>J: { ticket, url }
    J->>W: connect
    J->>W: {"ticket": "<jwt>"}
    W->>W: valida scope y expiración
    W-->>J: conexión registrada
    A-->>J: {"id":…, "title":…, "message":…}
```

Reglas:

- La conexión se acepta y **debe** enviar `{"ticket": "..."}` en los primeros 10 segundos; si no, se cierra con código `1008`.
- El ticket expira en 60 segundos y no sirve como token de acceso.
- Un usuario mantiene una sola conexión activa; una nueva reemplaza a la anterior.
- El cliente reconecta cada 5 segundos si la conexión cae.

### Entrega desde hilos de trabajo

Los endpoints HTTP son síncronos y se ejecutan en el *threadpool* de AnyIO, donde no hay un bucle de eventos activo. `notification_service` guarda, junto a cada socket, el bucle en el que fue aceptado y programa el envío con `asyncio.run_coroutine_threadsafe`. La publicación se hace **después del commit** de la transacción, evitando anunciar eventos que luego se revierten.

Formato del mensaje:

```json
{
  "id": 7,
  "user_id": 3,
  "title": "Adoption completed",
  "message": "Your adoption for Luna has been completed.",
  "type": "adoption_completed",
  "is_read": false,
  "related_pet_id": 12,
  "created_at": "2026-11-17T22:06:40"
}
```

---

## Capa de presentación (frontend)

### Rutas web (Flask)

| Ruta | Métodos | Protegida | Vista | Función |
| --- | --- | --- | --- | --- |
| `/` | `GET` | No | — | Redirige a panel o login |
| `/health` | `GET` | No | — | Sonda de disponibilidad |
| `/register` | `GET`, `POST` | No | `register.html` | Alta de cuenta |
| `/login` | `GET`, `POST` | No | `login.html` | Autenticación |
| `/logout` | `GET` | No | — | Cierra sesión |
| `/dashboard` | `GET` | Sí | `dashboard.html` | Mascotas, solicitudes recibidas y enviadas |
| `/my-pets/add` | `GET`, `POST` | Sí | `add_pet.html` | Alta con imagen |
| `/my-pets/<id>/toggle-adoption` | `POST` | Sí | — | Alterna publicación |
| `/my-pets/<id>/delete` | `POST` | Sí | — | Elimina una mascota |
| `/adopt/<id>` | `GET`, `POST` | Sí | `adopt.html` | Perfil + solicitud |
| `/adoptions/<id>/<action>` | `POST` | Sí | — | `approve`, `reject`, `complete` |
| `/notifications` | `GET` | Sí | `notifications.html` | Bandeja de avisos |
| `/notifications/<id>/read` | `POST` | Sí | — | Marca uno como leído |
| `/notifications/read-all` | `POST` | Sí | — | Marca todos |
| `/api/notifications` | `GET` | Sí | JSON | Proxy para el cliente JS |
| `/api/notifications/read-all` | `POST` | Sí | JSON | Proxy |
| `/api/ws-ticket` | `GET` | Sí | JSON | Ticket + URL del socket |

### Protección CSRF

- El token se genera con `secrets.token_urlsafe(32)` y se guarda en la sesión.
- Se expone a las plantillas con un `context_processor` e infiltra en cada formulario como `_csrf`.
- `before_request` valida **todo** `POST` comparando con `secrets.compare_digest`; acepta el valor por campo de formulario o por cabecera `X-CSRF-Token`.
- Un `POST` sin token válido no ejecuta la acción: muestra un aviso y redirige.

### Subida de imágenes

1. `MAX_CONTENT_LENGTH` rechaza peticiones sobredimensionadas con `413` y un mensaje amable.
2. Se leen los primeros bytes y se compara contra firmas reales: `FF D8 FF` (JPEG) y `89 50 4E 47 0D 0A 1A 0A` (PNG).
3. Se verifica el tamaño del flujo completo contra `MAX_UPLOAD_MB`.
4. El nombre lo genera el servidor (`uuid4().hex`), **ignorando** el nombre del cliente.
5. Se guarda en `fe/app/static/uploads` (volumen `fe_uploads` en Compose).
6. Se envía a la API una **ruta relativa** (`/static/uploads/<uuid>.png`), no una URL absoluta.
7. Si la API rechaza la creación, el archivo se elimina (rollback manual).

### Filtros Jinja

| Filtro | Comportamiento |
| --- | --- |
| `status_es` | `active → activo`, `pending → pendiente`, `adopted → adoptado`, `approved → aprobado`, `rejected → rechazado`, `completed → completado` |
| `species_es` | `dog → perro`, `cat → gato`, `rabbit → conejo`, `bird → ave` |
| `yesno_es` | `true → Sí`, `false → No` |
| `datetime_es` | ISO → `YYYY-MM-DD HH:MM` |

### Traducción de errores

`api_detail()` implementa una cascada: primero busca `error.code` en el diccionario de códigos; si no existe, busca `detail` en el diccionario de mensajes; en último caso usa un mensaje por defecto de la operación. Así la API responde en inglés técnico y la vista decide cómo presentarlo.

### Sistema visual

`style.css` define variables de color (crema, naranja `#d66a31`, verde azulado `#1f7a72`, oliva `#728244`), escala de radios (12/18/28 px), tipografía con fallbacks y un punto de ruptura en `860px`. Los añadidos de la versión endurecida son la insignia de no leídos, las tarjetas de solicitudes, los avisos emergentes y el estado de no leído.

---

## Seguridad

### Controles implementados

| Control | Implementación |
| --- | --- |
| Secretos fuera del código | `SECRET_KEY` obligatorio en `.env`; si falta, se genera una clave efímera y se registra una advertencia. No hay valores por defecto en el repositorio |
| Hashing de contraseñas | `passlib` con `bcrypt_sha256` |
| Política de contraseñas | 8–128 caracteres validados en Pydantic |
| Tokens | JWT HS256 con `exp`; el ticket WS usa `scope="ws"` y no es aceptado como token de acceso |
| Credenciales ausentes | `HTTPBearer(auto_error=False)` → `401` con `WWW-Authenticate` |
| Autorización por recurso | Verificación de `owner_id`; `403` explícito en lugar de `404` ambiguo |
| CSRF | Token por sesión y validación de todo `POST` |
| Cookies | `HttpOnly`, `SameSite=Lax` y `Secure` configurable (`COOKIE_SECURE`) |
| Subidas | Firma binaria, límite de tamaño y nombre generado por el servidor |
| Errores | Mensajes genéricos en `500` y `503`; trazas registradas en el servidor |
| CORS | Lista explícita y configurable; métodos y cabeceras acotados |
| Modo depuración | Desactivado por defecto (`DEBUG=false` en Compose); el depurador de Werkzeug nunca se expone |
| Base de datos | Puerto publicado solo en `127.0.0.1`; contraseña obligatoria desde el entorno |
| Contenedores | API sin `--reload`; frontend sin `debug`; ambos con healthcheck |

### Modelo de amenazas cubierto

- **XSS**: Jinja escapa por defecto y no se usa `|safe`; el cliente JS construye nodos con `textContent`.
- **Inyección SQL**: SQLAlchemy parametriza todas las consultas.
- **CSRF**: cubierto con token sincronizado.
- **Fixación de sesión**: `session.clear()` al iniciar sesión, con regeneración del token CSRF.
- **Enumeración de usuarios**: los mensajes de login no distinguen usuario inexistente de contraseña incorrecta.
- **Rutas de archivos**: el nombre de archivo del cliente se descarta por completo.

---

## Puesta en marcha

### Requisitos previos

- Docker Engine 20.10+ (o Podman 4+ con `podman-compose`)
- Docker Compose v2
- Puertos libres: `5000` (interfaz), `8000` (API), `5432` (PostgreSQL, solo `127.0.0.1`)

### 1. Configurar el entorno

```bash
cp .env.example .env

# Generar una clave de firma
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# Pegar el resultado en SECRET_KEY dentro de .env

# Definir también POSTGRES_PASSWORD con una contraseña real
```

Compose **falla de forma explícita** si `SECRET_KEY` o `POSTGRES_PASSWORD` no están definidos.

### 2. Levantar el stack

```bash
docker compose up --build
```

Al arrancar, el contenedor `be` ejecuta `alembic upgrade head` y luego Uvicorn. La primera vez crea el esquema completo.

| Servicio | URL |
| --- | --- |
| Interfaz | http://localhost:5000 |
| API + Swagger | http://localhost:8000/docs |
| Salud API | http://localhost:8000/health |
| Salud interfaz | http://localhost:5000/health |

```bash
# Logs
docker compose logs -f be

# Detener conservando datos
docker compose down

# Detener y borrar datos (incluye imágenes subidas)
docker compose down -v
```

> Con Podman: `podman-compose up -d --build` y `podman-compose down -v`.

### 3. Ejecución local sin contenedores

```bash
# --- Backend ---
cd be
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql+psycopg2://pawsuser:tuClave@localhost:5432/pawshome"
export SECRET_KEY="clave-local-de-desarrollo"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# --- Frontend (otra terminal) ---
cd fe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export API_BASE_URL="http://localhost:8000"
export SECRET_KEY="clave-local-de-desarrollo"
export DEBUG=true
python app/main.py
```

Requiere una instancia de PostgreSQL accesible en `DATABASE_URL`; el esquema lo crea Alembic.

---

## Variables de entorno

### Backend (`be`)

| Variable | Por defecto | Obligatoria | Descripción |
| --- | --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://pawsuser:pawspass@db:5432/pawshome` | Recomendada | Cadena de conexión SQLAlchemy |
| `SECRET_KEY` | *(clave efímera + advertencia)* | **Sí en producción** | Firma de JWT y tickets |
| `TOKEN_EXPIRE_MINUTES` | `60` | No | Vida del token de acceso |
| `WS_TICKET_EXPIRE_SECONDS` | `60` | No | Vida del ticket de WebSocket |
| `ALGORITHM` | `HS256` | No | Algoritmo de firma |
| `CORS_ORIGINS` | `http://localhost:5000,http://127.0.0.1:5000` | No | Orígenes permitidos |
| `DEBUG` | `false` | No | Bandera booleana |

### Frontend (`fe`)

| Variable | Por defecto | Obligatoria | Descripción |
| --- | --- | --- | --- |
| `API_BASE_URL` | `http://localhost:8000` | Sí en Docker | URL interna de la API |
| `SECRET_KEY` | *(clave efímera + advertencia)* | **Sí en producción** | Firma de la cookie de sesión |
| `WS_PUBLIC_URL` | `ws://localhost:8000/ws/notifications` | No | URL que usa el navegador para el socket |
| `MAX_UPLOAD_MB` | `5` | No | Tamaño máximo de imagen |
| `COOKIE_SECURE` | `false` | No | `true` solo bajo HTTPS |
| `REQUEST_TIMEOUT_SECONDS` | `10` | No | Timeout de las llamadas a la API |
| `DEBUG` | `false` | No | Activa el depurador de Flask (solo desarrollo) |

> `WS_PUBLIC_URL` debe ser alcanzable **desde el navegador**: usa `localhost` o el dominio público, nunca `http://be:8000`.

---

## Pruebas y calidad

La suite cubre autenticación, validación, aislamiento por propietario, ciclo completo de adopción, notificaciones y separación de credenciales. Se ejecuta contra SQLite en memoria, sin necesidad de PostgreSQL.

```bash
pip install -r be/requirements-dev.txt

# Todas las pruebas
pytest

# Solo lint
ruff check be fe

# Una prueba concreta
pytest be/tests/test_api.py::test_full_adoption_flow -v
```

Cobertura funcional actual (16 pruebas):

| Área | Casos |
| --- | --- |
| Sistema | `/health` |
| Cuentas | registro, login, usuario duplicado, contraseña corta |
| Autorización | rutas protegidas, token WS rechazado como token de acceso |
| Mascotas | alta, especie inválida, limpiar opcionales, `403` ajeno, borrado |
| Adopción | flujo completo, rechazo restaura disponibilidad, completar sin aprobar, solicitud duplicada, adoptar la propia |
| Notificaciones | listado, contador, marcado propio, `404` ajeno |

La CI (`.github/workflows/ci.yml`) ejecuta `ruff check be fe` y `pytest` en cada push a `main` y en cada pull request.

---

## Guía de usuario

### 1. Crear una cuenta

1. Abrir `http://localhost:5000`.
2. Pulsar **Registrarse**.
3. Completar usuario (3–50 caracteres), correo y contraseña (mínimo 8).
4. El sistema valida la unicidad contra la API y redirige al login.

**Errores frecuentes:** *«Ese nombre de usuario ya está registrado»*, *«Ese correo ya está registrado»*, *«Hay datos inválidos en el formulario»*.

### 2. Iniciar sesión

Introducir usuario y contraseña. El JWT queda en la cookie de sesión firmada y nunca se expone al navegador.

### 3. Agregar una mascota

1. En el panel, pulsar **Agregar una mascota**.
2. Completar nombre, especie (lista cerrada), raza, edad y descripción.
3. Subir una imagen JPEG o PNG de hasta 5 MB (obligatoria).
4. Marcar *Publicar esta mascota inmediatamente* si debe aparecer en el catálogo.
5. Guardar. La mascota aparece en el panel y, si se publicó, en el catálogo.

### 4. Administrar el catálogo

- **Publicar para adopción** / **Quitar de adopción** alterna la visibilidad.
- **Eliminar** borra la mascota y sus solicitudes (con confirmación).
- Las insignias muestran el estado (`activo`, `pendiente`, `adoptado`) y si está en catálogo.

### 5. Solicitar una adopción

1. Abrir **Catálogo**.
2. Elegir una tarjeta y pulsar **Iniciar solicitud de adopción**.
3. Escribir un mensaje para el dueño.
4. Enviar. El dueño recibe la solicitud y, si está conectado, un aviso en tiempo real.

**Reglas aplicadas:** no puedes solicitar tu propia mascota, no puedes duplicar una solicitud activa y la mascota debe seguir publicada y activa.

### 6. Gestionar solicitudes (dueño)

En **Panel → Solicitudes recibidas** cada tarjeta muestra mascota, solicitante, fecha, mensaje y estado:

| Estado | Acciones disponibles |
| --- | --- |
| `pending` | **Aprobar** · **Rechazar** |
| `approved` | **Completar adopción** · **Rechazar** |
| `completed` / `rejected` | Sin acciones |

- **Aprobar** retira la mascota del catálogo (estado `pending`) y avisa al adoptante.
- **Rechazar** devuelve la mascota al catálogo si no queda otra solicitud aprobada y avisa al adoptante.
- **Completar** transfiere la propiedad, marca la mascota como `adoptada`, rechaza a los solicitantes rivales y notifica a todos.

### 7. Seguir tus solicitudes (adoptante)

En **Panel → Mis solicitudes enviadas** se ve el estado de cada solicitud y la fecha de cierre.

### 8. Centro de avisos

El enlace **Avisos** de la barra superior muestra una insignia con el número de no leídos. Dentro de la página se puede marcar un aviso individualmente o usar **Marcar todo como leído**. Con la página abierta, los avisos nuevos aparecen como notificaciones emergentes sin recargar.

### 9. Cerrar sesión

El enlace con el nombre de usuario limpia la sesión y vuelve al login.

---

## Flujo funcional de una adopción

```mermaid
stateDiagram-v2
    [*] --> Publicada: dueño activa is_for_adoption
    Publicada --> Solicitada: adoptante envía /adoptions/request
    Solicitada --> Aprobada: dueño aprueba (mascota = pending)
    Solicitada --> Rechazada: dueño rechaza
    Aprobada --> Completada: dueño completa (transferencia)
    Aprobada --> Rechazada: dueño rechaza (mascota = active)
    Completada --> [*]
    Rechazada --> [*]

    note right of Aprobada
        Fuera del catálogo
        Notificación adoption_approved
    end note

    note right of Completada
        pets.owner_id = adopter_id
        pets.status = adopted
        Otras solicitudes → rejected
    end note
```

**Estados de la mascota:** `active` → (aprobación) `pending` → (cierre) `adopted`. Un rechazo devuelve `pending → active`.

---

## Decisiones de diseño

| Decisión | Justificación | Contrapartida |
| --- | --- | --- |
| API y UI en contenedores separados | Permite evolucionar la interfaz sin tocar el dominio | Dos despliegues y un salto de red |
| Flask SSR + un único JS | Sin build step; funciona sin JavaScript salvo el tiempo real | Interacciones más limitadas que una SPA |
| Repositorios con `flush`, servicios con `commit` | Atomicidad real en operaciones compuestas | Más disciplina: nunca confundir capas |
| Enums nativos de PostgreSQL | Integridad a nivel de motor | Cambiar valores exige nueva migración |
| Errores con código de máquina | El idioma no contamina la API | Diccionarios de traducción a mantener |
| Ticket WS de corta vida | Evita filtrar el JWT en URLs y logs | Un intercambio extra por conexión |
| Alembic como fuente del esquema | Cambios versionados y reversibles | Requiere disciplina de migraciones |
| Ruta relativa en `photo_url` | Independiente del host y del proxy | La imagen depende del origen del frontend |
| Imágenes en volumen | Sobreviven a reconstrucciones | No es un CDN; no escala horizontalmente |
| Registro WS en memoria | Implementación mínima | Una sola instancia de la API |

---

## Pendientes conscientes

Decisiones de alcance que quedaron fuera de esta iteración y por qué:

| Tema | Motivo | Ruta sugerida |
| --- | --- | --- |
| Escalado del WebSocket a varias réplicas | Requiere un bus pub/sub compartido | Redis + `redis.asyncio` como backend de conexiones |
| Almacenamiento de objetos (S3) | El volumen resuelve persistencia, no distribución | Migrar `photo_url` a URLs firmadas |
| Tokens de refresco | Se priorizó simplicidad y vida de 60 min | `refresh_token` + rotación |
| Cliente HTTP asíncrono en Flask | `requests` con timeout acota el riesgo actual | `httpx.AsyncClient` + vistas `async` |
| Purga del historial de Git | El destrackeo ya evita nuevos artefactos; reescribir historia es destructivo | `git filter-repo` con respaldo previo |
| Archivo `LICENSE` | Decisión legal del autor | Añadir MIT/Apache-2.0 |
| Verificación de correo y recuperación de contraseña | Fuera del alcance funcional inicial | Tokens de un solo uso + SMTP |

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| Compose falla con `Set SECRET_KEY in .env` | Falta `.env` o la variable está vacía | `cp .env.example .env` y completar los valores |
| El contenedor `be` reinicia en bucle | Migración fallida o base no disponible | `docker compose logs be`; revisar `db` y `DATABASE_URL` |
| «El servicio de autenticación no está disponible» | `be` caído o `API_BASE_URL` incorrecta | `docker compose ps` y logs del servicio |
| `413` al subir una imagen | Supera `MAX_UPLOAD_MB` | Reducir la imagen o subir el límite |
| «El archivo no es una imagen JPEG o PNG válida» | El contenido no coincide con la firma esperada | Convertir a JPEG/PNG real (renombrar no basta) |
| Las imágenes desaparecen tras `down -v` | `down -v` elimina el volumen `fe_uploads` | Evitar `-v` si los datos importan |
| Las imágenes se ven rotas en otro host | `photo_url` es relativa al frontend | Servir la interfaz en el host esperado o anteponer el origen correcto |
| El logout expulsa a todos tras reiniciar | `SECRET_KEY` efímera (no configurada) | Definir `SECRET_KEY` estable en `.env` |
| Los avisos en vivo no llegan | `WS_PUBLIC_URL` apunta a una dirección inalcanzable desde el navegador | Usar `ws://localhost:8000/...` o el dominio público |
| El socket cierra con `1008` | Ticket ausente, expirado o inválido | Recargar la página para obtener un ticket nuevo |
| `401` tras 60 minutos | El JWT expiró | Volver a iniciar sesión o ajustar `TOKEN_EXPIRE_MINUTES` |
| Cambios de esquema sin efecto | Falta una migración | `alembic revision --autogenerate` y `upgrade head` |
| `alembic` no encuentra `app` | Se ejecutó fuera de `/app` | Ejecutar dentro del contenedor o desde `be/` |
| Puerto 5432 ocupado | PostgreSQL local activo | Liberar el puerto; Compose solo lo expone en `127.0.0.1` |
| Cambios en `requirements.txt` sin efecto | Imagen cacheada | `docker compose build --no-cache be fe` |

---

## Glosario

| Término | Definición |
| --- | --- |
| **JWT** | *JSON Web Token*. Credencial firmada que transporta identidad y expiración |
| **Ticket WS** | JWT de corta vida con `scope="ws"` usado solo para el handshake del socket |
| **SSR** | *Server-Side Rendering*. El HTML se genera en el servidor |
| **Repository** | Capa que encapsula consultas y `flush`, sin confirmar transacciones |
| **Service** | Capa que aplica reglas de negocio y delimita transacciones |
| **Unidad de trabajo** | Conjunto de escrituras que se confirman o revierten como un todo |
| **CSRF** | *Cross-Site Request Forgery*; se mitiga con un token sincronizado por sesión |
| **Alembic** | Herramienta de migraciones de SQLAlchemy |
| **`is_for_adoption`** | Bandera que decide la visibilidad en el catálogo |
| **`previous_owner_id`** | Instantánea del dueño original, conservada tras la adopción |
| **Flash message** | Mensaje de una sola lectura mostrado tras una redirección |
| **Healthcheck** | Sonda periódica que determina si un contenedor está listo |

---

## Autoría

Proyecto desarrollado como actividad académica de arquitectura de software. Repositorio: `ActividadWebMascotas_20245221`.

Para contribuir: seguir la separación de capas descrita en [Arquitectura del sistema](#arquitectura-del-sistema), añadir una migración por cada cambio de modelo y mantener `ruff` y `pytest` en verde.
