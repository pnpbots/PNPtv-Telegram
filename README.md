# PNP Television Bot Ultimate

Bot de Telegram completo para gestión de suscripciones con soporte multicanal, pagos automáticos, broadcast segmentado y recordatorios de renovación.

## 🚀 Características Principales

### ✅ Funcionalidades Implementadas

1. **Selección de Idioma (EN/ES)** - Soporte completo bilingüe
2. **Verificación de Edad y Aceptación de Términos** - Proceso completo con persistencia
3. **Menú Principal Dinámico** - Con opciones contextuales y panel de admin
4. **Generación de Links Dinámicos** - Integración con Bold.co para pagos
5. **Registro Completo de Usuarios** - Base de datos PostgreSQL con estado persistente
6. **Control Automático de Suscripciones** - Activación y revocación automática
7. **Recordatorios de Renovación** - 3 días antes del vencimiento (configurable)
8. **Soporte Multicanal** - Hasta 5 canales por plan con asignación flexible
9. **Sistema de Broadcast Avanzado** - Segmentación por idioma, estado y tipo de usuario

### 🏗️ Arquitectura

```
bot_corregido/
├── bot/
│   ├── __init__.py
│   ├── config.py                    # Configuración central
│   ├── enhanced_subscriber_manager.py  # Gestión de suscripciones
│   ├── callbacks.py                 # Handlers de callbacks inline
│   ├── start.py                     # Lógica principal del bot
│   ├── payment_webhook.py           # Webhook de pagos seguro
│   ├── broadcast_manager.py         # Sistema de broadcast
│   ├── texts.py                     # Textos multiidioma
│   └── ...
├── run_bot.py                       # Punto de entrada principal
├── requirements.txt                 # Dependencias
├── railway.json                     # Configuración de Railway
├── supervisord.conf                 # Gestión de procesos
├── .env.example                     # Variables de entorno
└── README.md                        # Esta documentación
```

## 🛠️ Despliegue en Railway

### 1. Preparación

1. **Fork o clona este repositorio**
2. **Crea una cuenta en Railway.app**
3. **Configura una base de datos PostgreSQL en Railway**

### 2. Variables de Entorno Requeridas

Configura estas variables en Railway:

```bash
# Bot Configuration
BOT_TOKEN=tu_token_de_telegram_bot
ADMIN_IDS=123456789,987654321

# Payment Configuration
BOLD_IDENTITY_KEY=tu_clave_de_bold
BOLD_WEBHOOK_SECRET=secreto_webhook_bold

# Database (Railway lo proporciona automáticamente)
DATABASE_URL=postgresql://...

# Optional
CUSTOMER_SERVICE_CHAT_ID=id_del_chat_de_soporte
REMINDER_DAYS_BEFORE_EXPIRY=3
ENVIRONMENT=production
```

### 3. Configuración de Canales

Edita `bot/config.py` para configurar tus canales:

```python
CHANNELS = {
    "channel_1": -1002068120499,  # Reemplaza con tus IDs reales
    "channel_2": -1001234567890,
    "channel_3": -1001234567891,
    "channel_4": -1001234567892,
    "channel_5": -1001234567893,
}

# Asigna canales a planes
PLANS = {
    "trial": {
        "name": "Trial Trip",
        "price": "$14.99",
        "duration_days": 7,
        "link_id": "LNK_O7C5LTPYFP",
        "channels": ["channel_1"]  # Solo 1 canal para trial
    },
    # ... más planes
}
```

### 4. Despliegue

1. **Conecta tu repositorio a Railway**
2. **Railway detectará automáticamente `railway.json`**
3. **Las variables de entorno se configuran en el dashboard**
4. **El despliegue se ejecuta automáticamente**

### 5. Configuración del Webhook

Una vez desplegado, configura el webhook de Bold.co:

```
URL: https://tu-app.railway.app/webhook
Método: POST
```

## 🔧 Configuración Local (Desarrollo)

### 1. Instalación

```bash
git clone <tu-repositorio>
cd bot_corregido
pip install -r requirements.txt
```

### 2. Configuración

```bash
cp .env.example .env
# Edita .env con tus valores
```

### 3. Base de Datos Local

```bash
# Instala PostgreSQL localmente o usa Docker
docker run --name pnp-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres

# Actualiza DATABASE_URL en .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/pnp_bot
```

### 4. Ejecución

```bash
python run_bot.py
```

## 📊 Funcionalidades Detalladas

### Sistema de Suscripciones

- **Activación Automática**: Al recibir pago confirmado
- **Gestión de Canales**: Invitaciones automáticas por plan
- **Expiración Automática**: Revocación de acceso al vencer
- **Recordatorios**: Notificaciones antes del vencimiento

### Sistema de Broadcast

```python
# Segmentación disponible:
- Todos los usuarios
- Solo suscriptores activos  
- Suscripciones expiradas
- Nunca compraron
- Usuarios nuevos (7 días)

# Filtros de idioma:
- Todos los idiomas
- Solo inglés
- Solo español

# Tipos de contenido:
- Texto con formato Markdown
- Imágenes con caption
- Videos con caption
- GIFs con caption
```

### Panel de Administración

Comandos disponibles para administradores:

- `/broadcast` - Sistema de broadcast interactivo
- `/stats` - Estadísticas del bot
- `/reply [user_id] [mensaje]` - Responder a usuarios
- `/admin` - Panel de administración web

## 🔒 Seguridad

### Webhook de Pagos

- Verificación de firma HMAC (opcional)
- Validación de JSON
- Logging de seguridad
- Procesamiento asíncrono

### Base de Datos

- Pool de conexiones optimizado
- Queries parametrizadas (prevención SQL injection)
- Índices optimizados
- Logging de actividad

### Bot

- Validación de administradores
- Rate limiting implícito
- Manejo seguro de errores
- Logging estructurado

## 📈 Monitoreo y Logs

### Health Checks

- `GET /health` - Estado del servicio
- `GET /` - Información básica
- Verificación de conexión a BD

### Logging

```python
# Niveles configurables via LOG_LEVEL
- DEBUG: Información detallada
- INFO: Operaciones normales  
- WARNING: Situaciones anómalas
- ERROR: Errores que requieren atención
```

## 🚨 Solución de Problemas

### Problemas Comunes

1. **Bot no responde**
   - Verifica BOT_TOKEN
   - Revisa logs en Railway
   - Confirma que el bot esté iniciado

2. **Pagos no se procesan**
   - Verifica BOLD_IDENTITY_KEY
   - Confirma configuración del webhook
   - Revisa logs del webhook

3. **Usuarios no reciben invitaciones**
   - Verifica que el bot sea admin en los canales
   - Confirma IDs de canales en config.py
   - Revisa permisos del bot

4. **Base de datos no conecta**
   - Verifica DATABASE_URL
   - Confirma que PostgreSQL esté activo
   - Revisa configuración de red

### Logs Útiles

```bash
# En Railway, revisa:
- Deploy logs
- Application logs  
- Database logs

# Localmente:
tail -f /tmp/supervisord.log
```

## 🔄 Actualizaciones

### Despliegue de Cambios

1. **Push a tu repositorio**
2. **Railway redespliega automáticamente**
3. **Verifica logs de despliegue**
4. **Prueba funcionalidades críticas**

### Migraciones de BD

```python
# Las tablas se crean automáticamente
# Para cambios de esquema, modifica enhanced_subscriber_manager.py
# y reinicia el servicio
```

## 📞 Soporte

- **Email**: support@pnptv.app
- **Documentación**: Este README
- **Issues**: Repositorio de GitHub

## 📄 Licencia

Proyecto propietario - Todos los derechos reservados.

---

**Versión**: 2.0  
**Última actualización**: 2025-01-07  
**Compatibilidad**: Railway, PostgreSQL, Python 3.11+

