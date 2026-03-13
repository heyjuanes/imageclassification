# 🔍 VisionIA — Clasificador de Imágenes con IA

> Práctica 4 · Computación en la Nube · Universidad Autónoma de Occidente

**Equipo:**
Daniel Fernando Mejia · Ruben Dario Salcedo · Juan Espitia

---

## 🌐 Demo en vivo
**URL:** http://practica4-alb-1280823028.us-east-1.elb.amazonaws.com

Sube cualquier imagen y la IA te dice qué hay en ella con un porcentaje de confianza. Los resultados se guardan en una base de datos PostgreSQL.

---

## 🏗️ Arquitectura
```
Internet
    │
    ▼
[Application Load Balancer]  ← entrada pública
    │              │
    ▼              ▼
[EC2 - 1a]     [EC2 - 1b]   ← subredes privadas
[App + DB]     [App]
    │
    ▼
[PostgreSQL]   ← contenedor Docker
```

- **VPC** `10.0.0.0/16` con 2 zonas de disponibilidad
- **Subredes públicas** para el Load Balancer
- **Subredes privadas** para las instancias EC2
- **NAT Gateway** para que las instancias privadas accedan a internet
- **Security Groups** con política de mínimos privilegios

---

## 🐳 Contenedores

### Instancia 1 (us-east-1a) — App + Base de datos
```yaml
services:
  app:
    image: heyjuanes/sentimientos-ia:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_NAME=imagenes
    depends_on:
      - db
  db:
    image: postgres:15
```

### Instancia 2 (us-east-1b) — Solo App
```yaml
services:
  app:
    image: heyjuanes/sentimientos-ia:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=10.0.3.37
      - DB_NAME=imagenes
```

---

## 🧠 Aplicación de IA

Usa el modelo **google/vit-base-patch16-224** via Hugging Face API.

- Soporta imágenes JPG, PNG y WEBP
- Devuelve el Top 5 de predicciones con porcentaje de confianza
- Guarda el historial de clasificaciones en PostgreSQL

---

## 🔒 Seguridad

| Security Group | Permite |
|---|---|
| `alb-loadbalancer` | HTTP puerto 80 desde internet |
| `ec2-instancias` | Puerto 8000 solo desde el ALB |
| `db-postgres` | Puerto 5432 solo desde las EC2 |

---

## 🚀 Despliegue paso a paso

### 1. Infraestructura de red
```powershell
# VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Subredes públicas y privadas en us-east-1a y us-east-1b
aws ec2 create-subnet --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --cidr-block 10.0.3.0/24 --availability-zone us-east-1a

# Internet Gateway + NAT Gateway
aws ec2 create-internet-gateway
aws ec2 create-nat-gateway --subnet-id <subnet-publica>
```

### 2. Instancias EC2
```powershell
aws ec2 run-instances `
  --image-id ami-05024c2628f651b80 `
  --instance-type t3.micro `
  --key-name practica4-key `
  --subnet-id <subnet-privada> `
  --user-data <script>
```

### 3. User Data — instalación automática de Docker
```bash
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
useradd -m -s /bin/bash appuser
usermod -aG docker appuser
```

### 4. Imagen Docker
```bash
docker build -t heyjuanes/sentimientos-ia:latest .
docker push heyjuanes/sentimientos-ia:latest
```

### 5. Load Balancer
```powershell
aws elbv2 create-load-balancer --name practica4-alb --type application
aws elbv2 create-target-group --name practica4-tg --port 8000 --health-check-path /health
aws elbv2 register-targets --targets Id=<instancia1> Id=<instancia2>
```

---

## ✅ Prueba de alta disponibilidad

Se apagó la instancia 1 y se verificó que el Load Balancer redirigió el tráfico automáticamente a la instancia 2, confirmando la alta disponibilidad del sistema.

---

## 🐋 Docker Hub
`heyjuanes/sentimientos-ia:latest`