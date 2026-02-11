# Requisitos iniciales (MVP)

En la reunion con Carlo hablamos sobre el desarrollo de Aplicacion movil funcional (Mobile) que permita a un usuario:

- Hablarle a la app para indicarle que empiece a escuchar una reunion.
- Grabar el audio de la reunion sin requerir interaccion con la UI.
- Enviar ese audio a un backend.
- Transcribir el audio en el backend usando IA (por ejemplo, Whisper u otra alternativa).
- Procesar esa transcripcion para producir algo util (notas, resumen, entendimiento basico).
- Devolver el resultado al usuario.
- Tener todo el sistema funcionando end-to-end.

---

## Entendiendo las necesidades clave del usuario y que se debe hacer

1. Grabar con la voz, automatico, sin tocar la pantalla durante la reunion
2. Resumenes y acciones, no solo paginas y paginas de transcripcion
3. Verlo despues (horas o dias), con busqueda y filtros que funcionen bien
4. Te decimos que encontramos, sugerimos acciones, el audio siempre se guarda
5. Capturamos todo, detectamos automaticamente los compromisos que haces

---

## Limites

### Lo que si se va a desarrollar (en el mvp)

- App movil que graba con comandos de voz (sin tocar la pantalla)
- El backend va a procesar: transcribe, resume, saca puntos clave y sugiere acciones
- Webapp para revisar lo que se capturo y aprobar acciones (Anadir X a mi calendario)

### Lo que NO se desarrollara (en el mvp)

- No procesaremos en tiempo real por ahora, lo procesamos despues de forma async
- Chatbot conversacional, no es necesario para el MVP.
- No ejecucion automatica de acciones, solo sugerimos, no hacemos nada sin que el usuario apruebe
- Identificar quien dijo que: grabamos todo junto, sin separar por persona, aumenta dificultad por ahora y no es necesario para el MVP
- Revisar en movil: por ahora movil es para grabar, desktop para revisar

---

## MVP

### User flow

1. Usuario abre app mobile
2. Dice "Start listening" (voz)
3. App graba...
4. Usuario dice "Stop listening"
5. Se sube audio a cloud
6. Se transcribe con Whisper
7. Se resumen + puntos clave con LLM
8. Se guarda en database
9. Horas despues: Usuario abre web
10. Ve su memoria (resumen + puntos clave)
11. Puede leer transcript completo

![alt text](flujo.png)

### Decisiones tecnicas

**Como Activar App por voz**
Necesitamos comandos de voz como la interfaz principal para iniciar la grabacion y detenerla.

Hallazgos Importantes:

1. Inicio por voz esta bloqueado a nivel de sistema por parte de iOS, iOS bloquea wake words personalizados, Ninguna app puede estar "always listening" para iOS, por parte de android si se permited wake words si se usa un Foreground Service (Posiblemente nos encontremos con blockeos similares a los the apple por algunos "manufacturers" como Samsung, segun reportes en StackOverflow). Esto nos limita un poco y posiblemente la mejor solucion sea desarrollar aplicaciones con diferente tech stack y approach para cada SO.

_Posibles soluciones_:

iOS: Recientemente Apple lanzo AppIntents (con siri) https://developer.apple.com/documentation/appintents, podriamos aprovechar a Siri para iniciar la grabacion con nuestro aplicativo, algo asi como "Hey Siri, record with [nombre del aplicativo]"

Android: Implementacion de wake word mediante Foreground Service + deteccion local.

Una pequena decision aca: Me gustaria hacer un POC sobre app-intents y wake-words en iOS y Android, pero decidi de continuar con el Vertical Slice, para no gastar el tiempo.

_Decision_

- iOS: Siri AppIntents > app inicia grabacion
- Android: Foreground Service + on-device wake word detection (Posiblemente no para este POC)

**Envio del audio al servidor**

He considerado 2 metodos, WebRTC y AudioChunks

- Me llamo mucho la atencion el protocolo de WebRTC, por el streaming continuo de voz y la integracion de servicios de OpenAi https://developers.openai.com/api/docs/guides/realtime-webrtc. Podemos hacer cosas muy interesantes como crear entradas en calendarios practicamente real-time, es ultra-reactive
- Otra opcion es usar Audio Chunks, cuando finalice la grabacion, divido el audio en fragmentos de 1-5 segundos y envio cada chunk al Backend.

Cosas que estoy tomando en consideracion:

1. Latencia (gana webrtc)
2. Soporte offline: Este es el mayor factor decisivo, que pasa si la conexion es inestable para el usuario o la red se cae, adios conexion WebRTC, con Audio-Chunks guardamos y enviamos al server async.

_Decision_
Aunque me llama la atencion el protocolo WebRTC, considero que enviar el audio por chunks es mas "reliable", aburrido si, pero funciona. Me preocupa mucho el tema de conectividad y creo que es una opcion solida, ademas, podemos en el futuro implementar WebRTC si queremos desarrollar cosas locas.

---

**Procesamiento en Backend**

1. Async
   - Audio sube > Guardamos > Procesamos en background

**Async Pipeline**:

1. Audio Upload > guardamos en un bucket S3
2. Hacemos Trigger async job (SQS/Redis queue)
3. Backend procesa:
   - Whisper transcribe
   - Hacemos validacion de transcript
   - LLM Hace summary y key points
   - Hacemos validacion del output del LLM
   - Guardamos en PostgreSQL
4. Cambiamos el status en DB: "processing" > "ready"

_Me preocupan algunas posibles fallas y creo que debemos tener fallbacks_:

- Si Whisper falla > Guardamos audio sin transcript
- Si LLM falla > Guardamos transcript sin summary
- Tenemos un sistema de Retry, el audio SIEMPRE debe estar seguro ya sea en el movil o en el bucket.

_Tech Stack_

**Aplicativo Movil:**

iOS:

- Swift (nativo) + SwiftUI
- AVAudioRecorder para grabar
- AppIntents + Siri para activacion por voz
- URLSession para upload a S3

Android:

- Kotlin (nativo) + Jetpack Compose
- MediaRecorder para grabar
- Foreground Service para wake word detection
- Retrofit/OkHttp para upload a S3

Por que descartamos React Native:

- AppIntents es muy nuevo en iOS, React Native no lo soporta bien aun
- Foreground Service en Android tambien requiere codigo nativo especifico

**Backend:**

- Python + FastAPI
- PostgreSQL (Neon)
- Celery + Redis (para async jobs, o RQ mas simple)
- OpenAI SDK (Whisper + GPT-4 turbo)

**Web:**

- Next.js, React + TypeScript (full stack)

**Almacenamiento & Infraestructura:**

- S3 para almacenar audios
- RDS PostgreSQL para base de datos
- SQS para async queue (audio processing jobs)
- Lambda para procesar audios (Whisper + GPT-4)
- API Gateway para exponer endpoints REST
- CloudFront para servir web (o Amplify)
- OpenAI API para Whisper + GPT-4 turbo

---

## Deploy a AWS (Free Tier)

### Contexto

Despues de completar el backend (FastAPI + PostgreSQL + SQS + S3 + Lambda worker, 45 tests pasando), hicimos el deploy completo a AWS usando solo servicios del Free Tier para demostrar capacidades de DevOps y pipelines de deploy.

### Arquitectura desplegada

```
iOS App → EC2 t4g.micro (FastAPI en Docker) → RDS PostgreSQL (db.t3.micro)
               ↓                                      ↑
            S3 (audio)                           Lambda Worker
               ↓                                      ↑
            SQS Queue ────────────────────────────────┘
                                                       ↓
                                                  OpenAI API
```

### Servicios AWS

| Servicio | Que hace | Free Tier |
|----------|----------|-----------|
| EC2 t4g.micro | Corre la API FastAPI en Docker | 750 hrs/mes por 12 meses |
| RDS PostgreSQL | Base de datos (memorias, transcripts) | 750 hrs/mes db.t3.micro por 12 meses |
| S3 | Almacena archivos de audio | 5 GB por 12 meses |
| SQS + DLQ | Cola de mensajes para procesamiento async | 1M requests/mes (permanente) |
| Lambda | Worker que procesa audio (Whisper + GPT-4) | 1M requests/mes (permanente) |
| ECR | Almacena imagenes Docker | 500 MB (permanente) |

### Decisiones tecnicas clave

1. **EC2 en vez de App Runner**: App Runner requiere una suscripcion especial que las cuentas free-tier-only no tienen. EC2 t4g.micro (ARM) es free tier y corre Docker directamente.

2. **Redis deshabilitado en produccion**: ElastiCache no tiene free tier (~$15/mes). Implementamos `NullRedisClient` (clase no-op) y el frontend hace polling en vez de SSE.

3. **RDS publicamente accesible**: Para evitar el costo de NAT Gateway (~$30/mes) que se necesitaria con VPC privado. Seguridad via Security Groups que restringen el acceso.

4. **Lambda desde contenedor Docker**: Misma base de codigo que la API, un solo `requirements.prod.txt`, mas facil de testear localmente.

5. **SQS con Dead Letter Queue**: 3 reintentos antes de mover al DLQ (14 dias de retencion). Ningun mensaje se pierde.

### Infraestructura como Codigo (Terraform)

Todo definido en `terraform/` con archivos modulares:
- `main.tf` — Provider AWS, backend S3 para state
- `variables.tf` — Variables sensibles (db_password, openai_api_key)
- `network.tf` — VPC default, security groups
- `database.tf` — RDS PostgreSQL 16
- `s3.tf` — Bucket de audio con lifecycle 90 dias
- `sqs.tf` — Cola principal + DLQ
- `lambda.tf` — Lambda desde ECR con trigger SQS
- `apprunner.tf` — EC2 instance con Docker
- `iam.tf` — Roles IAM least-privilege
- `ecr.tf` — Repositorio de imagenes Docker

### CI/CD (GitHub Actions)

Pipeline en `.github/workflows/ci-cd.yml` con 3 stages:
1. **test** — Corre pytest (45 tests) en cada push/PR
2. **build-and-push** — Construye imagenes Docker (API + Lambda), push a ECR con SHA tags
3. **deploy** — Manual approval gate, terraform apply, actualiza Lambda y EC2

### Dockerfiles

- `backend/Dockerfile` — Multi-stage build (python:3.11-slim), corre uvicorn
- `backend/Dockerfile.lambda` — Base AWS Lambda Python 3.11, handler SQS

### Estado actual del deploy

- API corriendo en: `http://23.20.135.83:8000`
- Health check confirmado: `{"status":"ok","service":"rawk-backend"}`
- Todos los recursos AWS creados y funcionando

### Problemas encontrados y resueltos

1. **RDS backup retention**: Free tier no permite backups. Solucion: `backup_retention_period = 0`
2. **App Runner no disponible**: Cuentas free-tier-only no pueden usar App Runner. Solucion: EC2 t4g.micro con Docker
3. **Lambda image tag**: Referenciaba `:latest` pero pusheamos `:lambda-latest`. Corregido en terraform
4. **S3 lifecycle warning**: Faltaba bloque `filter {}`. Agregado
5. **IAM roles huerfanos**: Despues de remover App Runner del codigo, los roles quedaron en state. Limpieza con `terraform state rm`
