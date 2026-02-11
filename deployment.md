# Guia de Deployment - Memories

Notas para entender y poder explicar cada decision de deployment del proyecto.

---

## 1. Como funciona todo junto

```
                                 +------------------+
                                 |   iOS App        |
                                 |   (Memories)     |
                                 +--------+---------+
                                          |
                                          v
+------------------+           +----------+---------+           +------------------+
|   Web App        |           |   EC2 t4g.micro    |           |   RDS PostgreSQL |
|   (Next.js)      +---------->|   (FastAPI Docker)  +---------->|   (db.t3.micro)  |
+------------------+           +----+----------+----+           +------------------+
                                    |          |                        ^
                                    v          v                        |
                              +-----+--+  +---+----+                    |
                              |   S3   |  |  SQS   |                    |
                              | (audio)|  | (queue)|                    |
                              +-----+--+  +---+----+                    |
                                    ^         |                         |
                                    |         v                         |
                                    |   +-----+--------+               |
                                    |   |   Lambda     |               |
                                    +---+   Worker     +---------------+
                                        |              |
                                        +------+-------+
                                               |
                                               v
                                        +------+-------+
                                        |   OpenAI     |
                                        | (transcribe  |
                                        |  + analyze)  |
                                        +--------------+
```

**El flujo paso a paso:**

1. El usuario graba audio en la app de iOS.
2. El API (FastAPI corriendo en EC2 con Docker) recibe el archivo.
3. El API sube el audio a S3 y manda un mensaje a SQS para que se procese.
4. El API responde de una vez -- el usuario no tiene que esperar a que se procese.
5. SQS dispara el Lambda worker. Lambda baja el audio de S3, lo manda a OpenAI Whisper para transcribirlo, y despues a GPT-4 para el analisis.
6. Lambda guarda los resultados (transcripcion + memoria) en la base de datos PostgreSQL.
7. El cliente hace polling al API hasta que el procesamiento termine.

---

## 2. Servicios de AWS y limites del free tier

| Servicio | Que hace | Limite gratis |
|----------|----------|---------------|
| **EC2 t4g.micro** | Corre el API (FastAPI con Docker) | 750 hrs/mes por 12 meses |
| **RDS PostgreSQL** | Guarda las memorias, transcripciones, etc | 750 hrs/mes db.t3.micro por 12 meses |
| **S3** | Guarda los archivos de audio | 5 GB por 12 meses |
| **SQS** | Cola de mensajes para los jobs de procesamiento | 1M requests/mes (para siempre) |
| **Lambda** | Corre el worker que procesa el audio | 1M requests + 400K GB-seconds/mes (para siempre) |
| **ECR** | Guarda las imagenes de Docker del API y Lambda | 500 MB (para siempre) |

Lo importante: SQS, Lambda y ECR tienen free tier **permanente**. RDS y S3 se acaban despues de 12 meses. Por eso el costo sube un poco despues del primer ano.

---

## 3. Infraestructura como Codigo (Terraform)

### Que es Terraform y por que usarlo?

Terraform te deja definir toda tu infraestructura de nube en archivos de codigo en vez de andar haciendo click en la consola de AWS. Tres razones principales:

- **Reproducible**: Corres un comando y te crea la misma infraestructura cada vez. No mas "se me olvido marcar esa opcion en la consola".
- **Control de versiones**: Los cambios de infraestructura pasan por el mismo flujo de Git que el codigo -- PRs, reviews, historial.
- **Trabajo en equipo**: Cualquiera del equipo puede ver que esta desplegado con solo leer los archivos `.tf`.

### Comandos principales

| Comando | Que hace |
|---------|----------|
| `terraform init` | Descarga los providers (plugin de AWS), configura el backend de S3 para el state |
| `terraform plan` | Te muestra que va a cambiar sin cambiar nada (como un dry run) |
| `terraform apply` | Ejecuta los cambios de verdad -- crea/actualiza/destruye recursos |
| `terraform destroy` | Tumba todo lo que Terraform maneja. Un comando y listo. |

### El state file

Terraform tiene un "state file" que mapea tu codigo `.tf` a los recursos reales en AWS. Nuestro state esta guardado en S3:

```hcl
backend "s3" {
  bucket = "rawk-terraform-state"
  key    = "prod/terraform.tfstate"
  region = "us-east-1"
}
```

Por que importa tenerlo remoto:
- Si el state solo esta en tu laptop, nadie mas puede correr Terraform.
- Con S3, el pipeline de CI/CD y cualquier miembro del equipo puede hacer `terraform apply`.
- State locking (con DynamoDB) evita que dos personas apliquen cambios al mismo tiempo y corrompan el state.

### Archivos del proyecto

| Archivo | Para que sirve |
|---------|----------------|
| `main.tf` | Config de Terraform, providers (AWS ~> 5.0), backend en S3 |
| `variables.tf` | Variables: `aws_region`, `db_password` (sensitiva), `openai_api_key` (sensitiva), `environment`, `app_name` |
| `network.tf` | Busca la VPC default, security groups para RDS (puerto 5432 solo desde la VPC) y EC2 |
| `ecr.tf` | Repositorio de ECR para imagenes Docker, politica para quedarse solo con las ultimas 5 |
| `database.tf` | RDS PostgreSQL 16, db.t3.micro, accesible publicamente (trade-off del free tier), sin backups |
| `s3.tf` | Bucket de S3 para audio, acceso publico bloqueado, expiracion a 90 dias |
| `sqs.tf` | Cola de SQS con DLQ (3 reintentos, 14 dias de retencion en DLQ) |
| `iam.tf` | Roles de IAM: Lambda (SQS + S3 + logs), EC2 API (S3 + SQS + ECR) -- todos con permisos minimos |
| `lambda.tf` | Lambda function (imagen de container), trigger de SQS (batch size 1) |

---

## 4. Pipeline de CI/CD (GitHub Actions)

El pipeline esta en `.github/workflows/ci-cd.yml` y tiene tres etapas:

### Etapa 1: test

- **Se dispara**: En cada push y PR a `main` (cuando cambian archivos de `backend/` o `terraform/`).
- **Que hace**: Instala Python 3.11, instala dependencias, corre `pytest -v`.
- **Por que**: Para agarrar bugs antes de desplegar. Los 45 tests tienen que pasar.

### Etapa 2: build-and-push

- **Se dispara**: Solo en pushes a `main` (no en PRs), y solo si los tests pasaron.
- **Que hace**:
  1. Se autentica en AWS usando OIDC (sin guardar access keys).
  2. Login a ECR.
  3. Construye dos imagenes Docker: API (`Dockerfile`) y Lambda worker (`Dockerfile.lambda`).
  4. Las tagea con el SHA del commit (ej: `api-a1b2c3d`) mas un tag `latest`.
  5. Pushea las dos a ECR.

### Etapa 3: deploy

- **Se dispara**: Solo despues de que build-and-push termine bien.
- **Aprobacion manual**: Usa el environment `production` de GitHub, que puede requerir reviewers. Alguien tiene que darle "approve" antes de que corra el deploy.
- **Que hace**:
  1. Corre `terraform init` y `terraform apply -auto-approve`.
  2. Actualiza la Lambda con la nueva imagen.
  3. Despliega la nueva imagen del API en EC2.

### Por que la aprobacion manual?

Los deploys a produccion son medio irreversibles en el momento. Aunque puedes hacer rollback, es mucho mas seguro que un humano revise lo que va a cambiar antes de que se aplique.

### Autenticacion con OIDC

En vez de guardar access keys de AWS como GitHub Secrets (que se pueden filtrar), el pipeline usa OpenID Connect (OIDC). GitHub Actions recibe un token temporal de AWS en cada ejecucion. Si alguien compromete tu repo de GitHub, no puede sacar credenciales permanentes de AWS porque no existen.

---

## 5. Estrategia de Containers

### Por que Docker?

"En mi maquina si funciona" deja de ser problema. El mismo container que corre en local corre igual en EC2 y Lambda. Sin diferencias de ambiente.

### Multi-stage builds (Dockerfile del API)

```dockerfile
# Etapa 1: Instalar dependencias
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.prod.txt

# Etapa 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/
```

Por que dos etapas? La primera instala todas las herramientas de build y compila dependencias. La segunda solo copia lo compilado. El resultado es una imagen final mas chiquita -- sin compiladores, sin cache de pip, sin artifacts de build. Imagenes mas chiquitas = deploys mas rapidos y menos almacenamiento en ECR.

### Dos imagenes

| Imagen | Dockerfile | Para que |
|--------|-----------|----------|
| API | `backend/Dockerfile` | Corre `uvicorn` (FastAPI) en EC2 con Docker |
| Lambda worker | `backend/Dockerfile.lambda` | Basada en el runtime de AWS Lambda Python, corre el handler de SQS |

Las dos comparten el mismo codigo de `app/` y `requirements.prod.txt`, asi que la logica de negocio es identica.

### Por que Python 3.11 en containers si en local tengo 3.9?

El Python del sistema en macOS es 3.9.6. Pero en produccion, nosotros controlamos el runtime con Docker. Python 3.11 es significativamente mas rapido (10-60%) y tiene mejores mensajes de error. Como el container es el ambiente real de produccion, usamos la mejor version. En local, desarrollamos en un virtualenv y tenemos cuidado con la sintaxis (ej: usamos `Optional[str]` en vez de `str | None`).

---

## 6. Decisiones de Diseno y Trade-offs

### EC2 en vez de App Runner / ECS Fargate

**Decision**: Usar EC2 t4g.micro (ARM) corriendo Docker para el API.

**Por que**: App Runner requiere una suscripcion que las cuentas free-tier no tienen. ECS Fargate necesita ALB, target groups, task definitions -- demasiada configuracion para un demo. EC2 t4g.micro es gratis (750 hrs/mes), y simplemente corremos Docker con un script de user_data.

**Trade-off**: No hay auto-scaling, no hay TLS integrado, no hay load balancing. Para un demo con un usuario, esta perfecto. En produccion usarias App Runner o ECS Fargate con un ALB.

### Sin Redis en produccion

**Decision**: Redis deshabilitado (`REDIS_ENABLED=false`).

**Por que**: ElastiCache (Redis manejado) no esta en el free tier -- hasta la instancia mas chiquita cuesta ~$15/mes. Para un proyecto que apunta a $0/mes, no tiene sentido.

**Solucion**: En vez de usar Redis para publicar eventos en tiempo real (SSE), el frontend simplemente hace polling al API cada unos segundos. Polling esta bien para este caso -- de todas formas estas esperando una llamada a OpenAI que tarda 10-30 segundos.

### Lambda para el worker (en vez de ECS)

**Decision**: Usar Lambda disparado por SQS en vez de un container corriendo 24/7.

**Por que**:
- **Event-driven**: Lambda se dispara automaticamente cuando llega un mensaje a SQS. No hay que manejar un loop de polling.
- **Pagas por invocacion**: Solo pagas cuando hay procesamiento. Entre grabaciones, el costo es $0.
- **Escala a cero**: No hay containers idle quemando plata.
- **Escala automaticamente**: Si llegan 10 grabaciones a la vez, se levantan 10 instancias de Lambda.

**Trade-off**: Lambda tiene un timeout maximo de 15 minutos (nosotros pusimos 5). Si el procesamiento alguna vez toma mas que eso, Lambda no es la opcion. Para transcripcion de audio, 5 minutos es mas que suficiente.

### SQS con Dead Letter Queue (DLQ)

**Decision**: Los mensajes que fallan se reintentan 3 veces, y despues van a una DLQ que los guarda por 14 dias.

**Por que**: Si OpenAI esta caido temporalmente o hay un error transitorio, el mensaje se reintenta automatico. Despues de 3 fallos, el mensaje va a la DLQ en vez de perderse para siempre. Puedes inspeccionar la DLQ, arreglar el problema, y reenviar los mensajes.

**No se pierde nada.** Ese es el punto clave.

### Lambda en container en vez de zip

**Decision**: Empaquetar la Lambda como imagen de Docker en vez de un archivo zip.

**Por que**:
- Mismas dependencias que el API -- un solo `requirements.prod.txt`, sin manejar dependencias por separado.
- Un solo pipeline de build: el CI/CD construye las dos imagenes del mismo codebase.
- Mas facil de probar en local: `docker run` la imagen de Lambda con un evento de prueba.
- Los deployments con zip tienen un limite de 50MB (250MB descomprimido). Las imagenes de container pueden ser hasta 10GB.

### S3 para el state de Terraform

**Decision**: Guardar el state de Terraform en S3 en vez de localmente.

**Por que**:
- El pipeline de CI/CD necesita acceso al state para correr `terraform apply`.
- Si el state solo esta en tu laptop y tu laptop se dana, ya no puedes manejar la infraestructura.
- Con state remoto, cualquier persona o sistema autorizado puede correr Terraform.
- S3 tiene versionamiento -- puedes recuperar un state anterior si algo sale mal.

---

## 7. Seguridad

### IAM con permisos minimos

Cada servicio solo tiene los permisos que necesita. Si miras `iam.tf`:

- **Lambda** puede: leer de SQS, leer de S3, escribir logs a CloudWatch. Nada mas.
- **EC2 API** puede: escribir a S3 (subir audio), mandar mensajes a SQS, bajar imagenes de ECR. Nada mas.

Si Lambda se compromete, el atacante no puede escribir a S3 ni mandar mensajes a SQS. Si EC2 se compromete, el atacante no puede leer de SQS ni invocar Lambda.

### Sin secretos en el codigo

Los valores sensitivos (`db_password`, `openai_api_key`):
- Estan definidos como `sensitive = true` en `variables.tf` (Terraform los oculta de los logs).
- Estan guardados en GitHub Secrets.
- Se inyectan al momento del deploy como variables de ambiente `TF_VAR_*`.

No hay secretos en el codigo. No hay secretos en los archivos `.tf`. No hay secretos en las imagenes de Docker.

### OIDC para CI/CD

GitHub Actions se autentica en AWS sin access keys permanentes. El pipeline asume un IAM role via OIDC federation. Las credenciales temporales expiran cuando termina el workflow.

### RDS accesible publicamente (trade-off)

En este setup de free tier, RDS es accesible publicamente (pero con restricciones de security group) para evitar el costo del NAT Gateway (~$30/mes). El security group restringe el puerto 5432 al CIDR de la VPC.

**Para produccion**: Pondrias RDS en una subnet privada con `publicly_accessible = false` y usarias un NAT Gateway. Cuesta mas pero elimina cualquier exposicion publica de la base de datos.

### S3 con acceso publico bloqueado

```hcl
block_public_acls       = true
block_public_policy     = true
ignore_public_acls      = true
restrict_public_buckets = true
```

Los cuatro bloqueos de acceso publico estan activados. Los archivos de audio nunca estan expuestos al internet. Solo los roles de EC2 y Lambda (via IAM) pueden leer/escribir objetos.

---

## 8. Puntos para la Entrevista

Cosas que puedes decir con confianza:

- "Use **Terraform para infraestructura como codigo** porque hace la infraestructura reproducible, versionada, y revisable por el mismo flujo de Git que el codigo de la aplicacion."

- "El pipeline de CI/CD tiene una **aprobacion manual** porque desplegar a produccion debe ser una decision humana deliberada. Los tests pasan automaticamente, las imagenes se construyen automaticamente, pero alguien tiene que aprobar el deploy."

- "Use **EC2 con Docker** para el API porque App Runner no estaba disponible en mi cuenta free-tier y ECS Fargate requiere demasiada configuracion para un demo. El container de Docker es portable -- cambiar a App Runner o ECS en produccion es solo un cambio en Terraform."

- "**Lambda es ideal para el worker** porque es event-driven (se dispara por SQS), escala a cero cuando no se usa, y solo pagas por invocacion. No tiene sentido tener un container corriendo 24/7 esperando jobs de procesamiento ocasionales."

- "El **patron de DLQ asegura que no se pierdan mensajes**. Si el procesamiento falla tres veces, el mensaje va a una dead letter queue donde se retiene por 14 dias. Puedo inspeccionar los fallos, arreglar el problema, y reenviar los mensajes."

- "Implemente **degradacion elegante** -- si el analisis del LLM falla, igual guardamos la transcripcion. El usuario recibe su transcripcion aunque el paso de resumen con AI tenga un error."

- "Toda la infraestructura se puede **tumbar con un solo comando**: `terraform destroy`. No hay nada creado manualmente, asi que la limpieza es completa."

- "El pipeline corre **45 tests automatizados** antes de cualquier deployment. Los tests usan SQLite en memoria y AsyncMock asi que son rapidos y no necesitan credenciales reales de AWS u OpenAI."

- "Uso **autenticacion OIDC** para CI/CD en vez de access keys permanentes de AWS. Esto elimina el riesgo de que se filtren credenciales del repositorio de GitHub."

- "Cada servicio sigue **IAM con permisos minimos**. Lambda solo puede leer de S3 y SQS. El API en EC2 solo puede escribir a S3 y mandar a SQS. Si un servicio se compromete, el alcance del dano es limitado."

---

## 9. Costos

### Dentro del free tier (primeros 12 meses): ~$0/mes

| Servicio | Costo |
|----------|-------|
| EC2 t4g.micro | Gratis (750 hrs/mes) |
| RDS db.t3.micro | Gratis (750 hrs/mes) |
| S3 | Gratis (menos de 5 GB) |
| SQS | Gratis (menos de 1M requests) |
| Lambda | Gratis (menos de 1M invocaciones) |
| ECR | Gratis (menos de 500 MB, lifecycle deja solo 5 imagenes) |

### Despues de 12 meses (free tier de RDS + S3 expira): ~$15-20/mes

| Servicio | Costo estimado |
|----------|---------------|
| RDS db.t3.micro | ~$13/mes |
| S3 (unos pocos GB) | ~$0.10/mes |
| EC2 t4g.micro | ~$8/mes |
| SQS | Sigue gratis (para siempre) |
| Lambda | Sigue gratis (para siempre) |
| ECR | Sigue gratis (para siempre) |
| **Total** | **~$21-23/mes** |

### Como tumbar todo

```bash
cd terraform
terraform destroy
```

Esto elimina todos los recursos de AWS. Lo unico que queda es el bucket de S3 del state de Terraform (que lo borras manualmente si quieres dejar la cuenta completamente limpia).

---

## 10. Comandos Utiles

### Desarrollo local

```bash
# Levantar dependencias del backend (PostgreSQL + Redis)
cd backend
docker compose up -d

# Activar virtualenv y correr el API
source venv/bin/activate
uvicorn app.main:app --reload

# Correr tests
python -m pytest -v
```

### Docker

```bash
# Construir imagen del API
docker build -t memories-api -f backend/Dockerfile backend/

# Construir imagen de Lambda
docker build -t memories-lambda -f backend/Dockerfile.lambda backend/

# Correr API localmente en Docker
docker run -p 8000:8000 --env-file .env memories-api
```

### Terraform

```bash
cd terraform

# Inicializar (descarga providers, conecta al backend de S3)
terraform init

# Ver que va a cambiar (dry run)
terraform plan

# Aplicar cambios (crea/actualiza recursos)
terraform apply

# Tumbar todo
terraform destroy

# Ver el state actual
terraform show

# Ver un recurso especifico
terraform state show aws_lambda_function.sqs_processor
```

### ECR (push manual de imagenes)

```bash
# Login a ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag y push
docker tag memories-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/rawk-backend:api-latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/rawk-backend:api-latest
```

### Comandos utiles de AWS CLI

```bash
# Ver estado de la instancia EC2
aws ec2 describe-instances --filters "Name=tag:Name,Values=rawk-api" --query "Reservations[].Instances[].{ID:InstanceId,State:State.Name,IP:PublicIpAddress}"

# Ver la Lambda function
aws lambda get-function --function-name rawk-sqs-processor

# Ver cuantos mensajes hay en la cola de SQS
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessages

# Ver la DLQ por mensajes fallidos
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names ApproximateNumberOfMessages

# Ver logs de Lambda
aws logs tail /aws/lambda/rawk-sqs-processor --follow
```
