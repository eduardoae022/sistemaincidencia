# Sistema de Gestión de Incidencias — URBINMOBILIARIA S.A.C.

Sistema web para la gestión de incidencias de TI, desarrollado como instrumento de
recolección de datos para una tesis de Ingeniería de Sistemas sobre priorización
de incidentes con Machine Learning.

**Fase 1:** Gestor de incidencias completo (este repositorio)
**Fase 2:** Integración con modelos ML (Random Forest, SVM, XGBoost) — próximamente

---

## Requisitos previos

| Herramienta | Versión mínima |
|---|---|
| Python | 3.11+ |
| MySQL | 8.0+ |
| pip | 23+ |

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd sistema_incidencia
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Activar en Windows:
.\venv\Scripts\activate

# Activar en Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear la base de datos en MySQL

Conéctese a MySQL y ejecute:

```sql
CREATE DATABASE incidencias_urbinmobiliaria
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 5. Configurar variables de entorno

Copie el archivo de ejemplo y edítelo:

```bash
copy .env.example .env
```

Edite `.env` con sus credenciales reales:

```env
SECRET_KEY=django-insecure-cambiar-en-produccion-...
DEBUG=True
DB_NAME=incidencias_urbinmobiliaria
DB_USER=root
DB_PASSWORD=su_contraseña_mysql
DB_HOST=localhost
DB_PORT=3306
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

> ⚠️ Nunca suba `.env` al repositorio. Está en `.gitignore`.

### 6. Aplicar migraciones

```bash
python manage.py migrate
```

### 7. Cargar datos iniciales (roles, usuarios, catálogos, SLA)

```bash
python manage.py cargar_datos_iniciales
```

Esto crea automáticamente:
- 4 grupos de roles
- 4 usuarios de prueba (uno por rol)
- 5 categorías de incidencia
- 19 servicios afectados de ejemplo
- Valores de SLA: Alta=4h, Media=24h, Baja=72h

### 8. Crear superusuario (opcional — para acceso al admin Django)

```bash
python manage.py createsuperuser
```

### 9. Iniciar el servidor de desarrollo

```bash
python manage.py runserver
```

Acceda a: **http://localhost:8000**

---

## Usuarios de prueba (creados por `cargar_datos_iniciales`)

| Usuario | Contraseña | Rol |
|---|---|---|
| `solicitante1` | `Solicitante2024!` | Solicitante |
| `operador1` | `Operador2024!` | Operador de Mesa de Ayuda |
| `tecnico1` | `Tecnico2024!` | Técnico de Soporte |
| `admin1` | `Admin2024!` | Administrador |

> ⚠️ Cambie estas contraseñas antes de usar en producción.

---

## Flujo de trabajo principal

```
1. Solicitante → registra incidencia (descripción + servicio)
2. Operador    → clasifica (categoría, prioridad, SLA calculado)
3. Operador    → asigna técnico
4. Técnico     → "Tomar ticket" (estampa fecha_hora_primera_atención — TPA)
5. Técnico     → resuelve con solución documentada (calcula dentro_SLA)
6. Operador    → cierra definitivamente
7. Admin       → valida prioridad correcta (ground truth para ML)
8. Admin       → exporta dataset CSV para Fase 2
```

---

## Estructura del proyecto

```
sistema_incidencia/
├── config/                 # Configuración de Django (settings, urls, wsgi)
├── apps/
│   ├── usuarios/           # Autenticación, roles, perfiles
│   ├── tickets/            # Ticket (modelo central), flujo de estados, bitácora
│   ├── catalogos/          # Categoría, ServicioAfectado, SLA
│   └── reportes/           # Dashboard, exportación Excel/CSV
├── templates/              # Templates HTML por app
├── static/
│   └── css/main.css        # Estilos propios (Bootstrap 5 + diseño corporativo)
├── .env                    # Variables de entorno (NO subir al repo)
├── .env.example            # Plantilla de variables
├── requirements.txt
└── manage.py
```

---

## Módulos del sistema

### Para el Solicitante
- Registrar incidencias (descripción + servicio afectado)
- Ver el estado de sus propios tickets
- Comentar en sus tickets

### Para el Operador de Mesa de Ayuda
- Ver todos los tickets nuevos
- Clasificar: categoría, servicio, prioridad (línea base para ML)
- Asignar técnicos
- Cerrar tickets resueltos
- Ver dashboard y exportar datos

### Para el Técnico de Soporte
- Ver tickets asignados a él
- "Tomar ticket" (registra TPA)
- Documentar solución y resolver
- Poner en espera si necesita información

### Para el Administrador
- Todo lo anterior
- Gestión de usuarios y roles
- CRUD de catálogos (categorías, servicios, SLA)
- Bitácora de auditoría completa
- Exportación de dataset para ML (Tabla 5 de la tesis)
- Validar prioridad correcta (ground truth)

---

## KPIs del sistema (Fase 1 → datos para Fase 2)

| Indicador | Descripción |
|---|---|
| **TCC** | Tasa de Clasificación Correcta: % de tickets donde prioridad_operador = prioridad_correcta |
| **TPA** | Tiempo de Primera Atención: horas desde registro hasta "Tomar ticket" |
| **TAO** | Tasa de Atención Oportuna: % de tickets cerrados dentro del SLA |

---

## Dataset de entrenamiento (Fase 2)

El botón "Exportar Dataset (CSV)" genera un archivo con la estructura de la Tabla 5 de la tesis:

- ID Ticket, Fecha registro, Categoría, Servicio afectado, Descripción
- Prioridad operador (variable objetivo para ML)
- Prioridad correcta (ground truth)
- Horas transcurridas, SLA máximo, ¿Dentro del SLA?
- ID solicitante anonimizado (sin datos personales)

El export excluye reaperturas y tickets con datos incompletos por defecto.

---

## Variables de entorno requeridas

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django | `django-insecure-...` |
| `DEBUG` | Modo debug | `True` / `False` |
| `DB_NAME` | Nombre de la base de datos | `incidencias_urbinmobiliaria` |
| `DB_USER` | Usuario de MySQL | `root` |
| `DB_PASSWORD` | Contraseña de MySQL | `mi_contraseña` |
| `DB_HOST` | Host de MySQL | `localhost` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `EMAIL_BACKEND` | Backend de email | `django.core.mail.backends.console.EmailBackend` |

---

## Comandos útiles de gestión

```bash
# Verificar configuración
python manage.py check

# Crear migraciones (después de cambiar modelos)
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Recargar datos iniciales (idempotente)
python manage.py cargar_datos_iniciales

# Colectar archivos estáticos (producción)
python manage.py collectstatic

# Shell de Django (depuración)
python manage.py shell
```

---

## Nota sobre Fase 2 (Machine Learning)

Los campos `prioridad_modelo` y `confianza_modelo` ya existen en la tabla `Ticket`
pero no se muestran en la interfaz. En Fase 2, se integrarán llenando estos campos
mediante un único endpoint, sin modificar la estructura existente.

---

*URBINMOBILIARIA S.A.C. — Tesis de Ingeniería de Sistemas*
