$readme = @'
# LET HIM COOK 🔥
### Asistente de Recetas con Inteligencia Artificial

> **Computacion en la Nube — Practica 4**
> Universidad Autonoma de Occidente

**Equipo:**
Daniel Fernando Mejia · Ruben Dario Salcedo · Juan Espitia

---

## Demo en vivo
**URL:** http://practica4-alb-1280823028.us-east-1.elb.amazonaws.com

Dile a la IA que ingredientes tienes en tu nevera y ella genera una receta completa con pasos detallados, tiempo de preparacion, porciones y un consejo de chef. Cada receta se guarda en una base de datos PostgreSQL y puedes exportarla en PDF.

---

## Que hace la app?

1. El usuario escribe los ingredientes que tiene disponibles
2. La app envia los ingredientes a la API de Groq (Llama 3.3 70B)
3. La IA genera una receta completa en formato JSON estructurado
4. La receta se muestra con pasos desplegables e interactivos
5. Se guarda en PostgreSQL con fecha y hora
6. El usuario puede exportar la receta en PDF, generar una alternativa o borrar el historial

---

## Arquitectura
```
                         Internet
                            |
                            v
               [Application Load Balancer]
                puerto 80 — acceso publico
                   |                |
                   v                v
          [EC2 — us-east-1a]  [EC2 — us-east-1b]
           subred privada       subred privada
           10.0.3.37            10.0.4.154
           [App + PostgreSQL]   [App]
                   |
                   v
             [PostgreSQL 15]
              puerto 5432
                   |
                   v
             [API de Groq]
          llama-3.3-70b-versatile
```

### Componentes de la infraestructura

**VPC (10.0.0.0/16)**
Red virtual privada que aísla toda la infraestructura de AWS. Ningún recurso interno es accesible directamente desde internet excepto a través del Load Balancer.

**Subredes publicas (10.0.1.0/24 y 10.0.2.0/24)**
Alojan el Application Load Balancer. Tienen una ruta directa al Internet Gateway, lo que les permite recibir trafico desde internet.

**Subredes privadas (10.0.3.0/24 y 10.0.4.0/24)**
Alojan las instancias EC2 con la aplicacion. No tienen IP publica ni acceso directo desde internet. Solo reciben trafico del Load Balancer.

**Internet Gateway**
Componente que conecta la VPC con internet. Permite que el Load Balancer reciba peticiones externas.

**NAT Gateway**
Permite que las instancias en subredes privadas accedan a internet de forma saliente (para descargar imagenes Docker, llamar la API de Groq, etc.) sin estar expuestas a conexiones entrantes.

**Application Load Balancer (ALB)**
Distribuye el trafico HTTP entrante entre las dos instancias EC2. Realiza health checks cada 30 segundos al endpoint /health. Si una instancia falla, el ALB deja de enviarle trafico automaticamente.

**Instancias EC2 (t3.micro)**
Dos instancias Amazon Linux 2 en zonas de disponibilidad diferentes. Docker y Docker Compose se instalan automaticamente al lanzarlas mediante User Data. Los contenedores corren bajo el usuario appuser sin privilegios root.

**PostgreSQL en Docker**
Corre como contenedor en la instancia 1. La instancia 2 se conecta a ella via IP privada. Los datos persisten en un volumen Docker nombrado.

**Bastion Host**
Instancia publica que sirve como puente para conectarse via SSH a las instancias privadas. Es la unica forma de acceder directamente a las instancias.

---

## Seguridad — Politica de minimos privilegios

Cada Security Group permite unicamente el trafico estrictamente necesario:

| Security Group | Puerto | Origen | Proposito |
|---|---|---|---|
| alb-loadbalancer | 80 | 0.0.0.0/0 | Recibir HTTP desde internet |
| ec2-instancias | 8000 | Solo desde el ALB | Recibir trafico de la app |
| ec2-instancias | 22 | Solo desde el Bastion | Acceso SSH administrativo |
| db-postgres | 5432 | Solo desde las EC2 | Acceso a la base de datos |
| bastion-host | 22 | 0.0.0.0/0 | SSH de administracion |

Las instancias EC2 no tienen IP publica. El unico acceso SSH es a traves del Bastion Host. Los contenedores corren bajo el usuario appuser que pertenece al grupo docker pero no tiene privilegios sudo.

---

## Docker y Docker Compose

Docker permite empaquetar la aplicacion con todas sus dependencias en una imagen reproducible que corre de forma identica en cualquier servidor. Docker Compose orquesta multiples contenedores con un solo comando.

### Instancia 1 — App + Base de datos
```yaml
services:
  app:
    image: heyjuanes/chef-ia:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_NAME=recetas
      - DB_USER=postgres
      - DB_PASSWORD=postgres123
      - GROQ_API_KEY=...
    depends_on:
      - db
    restart: always

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=recetas
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres123
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: always

volumes:
  pgdata:
```

### Instancia 2 — Solo App
```yaml
services:
  app:
    image: heyjuanes/chef-ia:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=10.0.3.37
      - DB_NAME=recetas
      - DB_USER=postgres
      - DB_PASSWORD=postgres123
      - GROQ_API_KEY=...
    restart: always
```

La instancia 2 no tiene base de datos propia. Se conecta a PostgreSQL en la instancia 1 usando su IP privada (10.0.3.37). Esto es posible porque ambas instancias estan en la misma VPC y el Security Group de la base de datos permite trafico desde las EC2.

---

## Inteligencia Artificial

### Modelo utilizado
**Llama 3.3 70B Versatile** via API de Groq. Es un modelo de lenguaje de 70 mil millones de parametros desarrollado por Meta, accesible gratuitamente a traves de Groq con tiempos de respuesta extremadamente rapidos (menos de 3 segundos).

### Como funciona la generacion de recetas
El sistema le pide al modelo que responda siempre en formato JSON estructurado con nombre del plato, tiempo, porciones, dificultad, lista de ingredientes con cantidades, pasos con titulo y detalle explicativo, y un consejo de chef. Esto permite que el frontend muestre la informacion de forma organizada y bonita.

### Flujo completo de una peticion
1. El usuario escribe los ingredientes en el textarea
2. El frontend envia un POST a /generar con los ingredientes en JSON
3. Flask recibe la peticion y llama a la API de Groq
4. Groq procesa los ingredientes con Llama 3.3 y devuelve la receta en JSON
5. Flask guarda la receta en PostgreSQL
6. El frontend renderiza la receta con pasos interactivos desplegables
7. El usuario puede exportar la receta como PDF con diseno dark mode

---

## Stack tecnologico

| Capa | Tecnologia |
|---|---|
| Backend | Python 3.11 + Flask |
| IA | Groq API + Llama 3.3 70B |
| Base de datos | PostgreSQL 15 |
| Contenedores | Docker + Docker Compose |
| Infraestructura | AWS EC2, VPC, ALB, NAT Gateway |
| Frontend | HTML + CSS + JavaScript vanilla |
| PDF | jsPDF 2.5.1 |

---

## Despliegue paso a paso

### Requisitos previos
- Cuenta de AWS con permisos EC2, VPC, ELB e IAM
- AWS CLI configurado con `aws configure`
- Docker Desktop instalado
- Cuenta en Docker Hub
- Cuenta en Groq (console.groq.com) para obtener API key gratuita

### 1. Crear infraestructura de red
```powershell
# VPC
$vpcId = (aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)

# Subredes publicas
$pubSubnet1 = (aws ec2 create-subnet --vpc-id $vpcId --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
$pubSubnet2 = (aws ec2 create-subnet --vpc-id $vpcId --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)

# Subredes privadas
$privSubnet1 = (aws ec2 create-subnet --vpc-id $vpcId --cidr-block 10.0.3.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
$privSubnet2 = (aws ec2 create-subnet --vpc-id $vpcId --cidr-block 10.0.4.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)

# Internet Gateway
$igwId = (aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $igwId --vpc-id $vpcId

# NAT Gateway
$eipAlloc = (aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
$natGwId = (aws ec2 create-nat-gateway --subnet-id $pubSubnet1 --allocation-id $eipAlloc --query 'NatGateway.NatGatewayId' --output text)
aws ec2 wait nat-gateway-available --nat-gateway-ids $natGwId
```

### 2. Security Groups
```powershell
# ALB — acepta HTTP desde internet
$sgAlb = (aws ec2 create-security-group --group-name "alb-loadbalancer" --description "SG ALB" --vpc-id $vpcId --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $sgAlb --protocol tcp --port 80 --cidr 0.0.0.0/0

# EC2 — acepta trafico solo desde el ALB
$sgEc2 = (aws ec2 create-security-group --group-name "ec2-instancias" --description "SG EC2" --vpc-id $vpcId --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $sgEc2 --protocol tcp --port 8000 --source-group $sgAlb

# PostgreSQL — acepta trafico solo desde las EC2
$sgDb = (aws ec2 create-security-group --group-name "db-postgres" --description "SG DB" --vpc-id $vpcId --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $sgDb --protocol tcp --port 5432 --source-group $sgEc2
```

### 3. Instancias EC2 con Docker via User Data
```powershell
$userData = @'
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
useradd -m -s /bin/bash appuser
usermod -aG docker appuser
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
'@

$userDataB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($userData))

# Instancia 1 en us-east-1a
$instance1 = (aws ec2 run-instances `
  --image-id ami-05024c2628f651b80 `
  --instance-type t3.micro `
  --key-name practica4-key `
  --subnet-id $privSubnet1 `
  --security-group-ids $sgEc2 `
  --user-data $userDataB64 `
  --query 'Instances[0].InstanceId' --output text)

# Instancia 2 en us-east-1b
$instance2 = (aws ec2 run-instances `
  --image-id ami-05024c2628f651b80 `
  --instance-type t3.micro `
  --key-name practica4-key `
  --subnet-id $privSubnet2 `
  --security-group-ids $sgEc2 `
  --user-data $userDataB64 `
  --query 'Instances[0].InstanceId' --output text)
```

### 4. Construir y publicar imagen Docker
```bash
docker build -t heyjuanes/chef-ia:latest .
docker push heyjuanes/chef-ia:latest
```

### 5. Desplegar contenedores en las instancias
```bash
# Conectarse via Bastion Host
ssh -i practica4-key.pem ec2-user@<bastion-ip>
ssh -i practica4-key.pem ec2-user@<ip-privada>

# Cambiar a usuario sin privilegios root
sudo su - appuser
cd ~/app

# Levantar contenedores
docker-compose up -d
```

### 6. Application Load Balancer
```powershell
# Crear ALB en subredes publicas
$albArn = (aws elbv2 create-load-balancer `
  --name practica4-alb `
  --subnets $pubSubnet1 $pubSubnet2 `
  --security-groups $sgAlb `
  --type application `
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Target Group con health check en /health
$tgArn = (aws elbv2 create-target-group `
  --name practica4-tg `
  --protocol HTTP --port 8000 `
  --vpc-id $vpcId `
  --health-check-path /health `
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Registrar instancias
aws elbv2 register-targets --target-group-arn $tgArn `
  --targets Id=$instance1,Port=8000 Id=$instance2,Port=8000

# Crear listener
aws elbv2 create-listener --load-balancer-arn $albArn `
  --protocol HTTP --port 80 `
  --default-actions Type=forward,TargetGroupArn=$tgArn
```

---

## Alta disponibilidad

El sistema esta disenado para tolerar la falla de cualquiera de las dos instancias EC2 sin interrupcion del servicio.

**Prueba realizada:**
1. Con ambas instancias activas se verifico que la app respondia correctamente
2. Se apago la instancia 1 con `aws ec2 stop-instances --instance-ids i-07e6fe2148a7aee68`
3. El ALB detecto el fallo en el siguiente health check (maximo 30 segundos)
4. Todo el trafico fue redirigido automaticamente a la instancia 2
5. La app siguio funcionando sin ninguna interrupcion para el usuario
```powershell
# Verificar estado de los targets
aws elbv2 describe-target-health `
  --target-group-arn <tg-arn> `
  --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]' `
  --output table
```

---

## Estructura del repositorio
```
lethimcook/
├── app.py                  # Backend Flask — endpoints y logica de negocio
├── requirements.txt        # Dependencias Python
├── Dockerfile              # Imagen Docker de la aplicacion
├── docker-compose.yml      # Configuracion multi-container
├── templates/
│   └── index.html          # Frontend — interfaz dark mode estilo Netflix
└── README.md               # Este archivo
```

---

## Imagen en Docker Hub
```
heyjuanes/chef-ia:latest
```
```bash
docker pull heyjuanes/chef-ia:latest
docker run -p 8000:8000 -e GROQ_API_KEY=tu_key heyjuanes/chef-ia:latest
```

---

## Conclusiones

Este proyecto demostro en la practica como se construye una arquitectura de nube moderna, robusta y escalable desde cero usando AWS. Cada componente tiene un proposito especifico y bien definido.

La VPC aísla y protege la infraestructura. El NAT Gateway permite que los servidores privados accedan a internet sin exponerse. Los Security Groups garantizan que solo el trafico necesario fluya entre componentes aplicando el principio de minimos privilegios. El Load Balancer elimina el punto unico de falla distribuyendo la carga entre dos zonas de disponibilidad distintas.

La contenedorizacion con Docker fue clave para lograr despliegues consistentes y reproducibles. Una misma imagen construida una sola vez corre de forma identica en ambas instancias sin importar diferencias de entorno. Docker Compose simplifica la orquestacion permitiendo levantar la aplicacion y la base de datos con un solo comando.

La prueba de alta disponibilidad fue el momento mas revelador: al apagar una instancia completa, el sistema no cayo. El Load Balancer detecto el fallo en segundos y redirigió el trafico automaticamente sin que el usuario notara ninguna interrupcion. Esto es exactamente lo que distingue una arquitectura de produccion de un servidor comun.

La integracion con la API de Groq demuestra como los modelos de lenguaje de ultima generacion pueden transformar una aplicacion simple en una herramienta de IA util y accesible. Llama 3.3 70B genera recetas detalladas, creativas y bien estructuradas en menos de 3 segundos, algo impensable con modelos locales en instancias t3.micro.

En definitiva, AWS no es solo infraestructura rentada — es un ecosistema de servicios que bien combinados permiten construir sistemas que se comportan como los de las grandes empresas tecnologicas del mundo.
'@

[System.IO.File]::WriteAllText("$env:USERPROFILE\practica4-ia\README.md", $readme, [System.Text.Encoding]::UTF8)
Write-Host "README creado"
