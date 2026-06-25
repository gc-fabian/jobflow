# JobFlow by Corocul

JobFlow by Corocul es una herramienta privada para buscar, filtrar y preparar postulaciones laborales para Fabián Godoy Casas.

Nombre recomendado: **JobFlow by Corocul**. Repo sugerido: `jobflow`.

Principios:
- No inventa experiencia: usa perfil base configurable y deja marcadores `[COMPLETAR]`.
- No envía postulaciones automáticamente: prepara CV/mensaje/checklist y tú confirmas/envías.
- LinkedIn: funciona mejor con links públicos o CSV/export manual. Para búsqueda personalizada requiere que tú abras sesión en tu navegador y pegues links/ofertas al sistema.

## Uso rápido

```bash
cd C:\Users\56989\Documents\job-application-copilot
python -m jobcopilot init
python -m jobcopilot add-url "https://login.airavirtual.com/postula/sTukEeeW3s8leyn1Y80e" --company Sercomed --role "Ingeniero de Software"
python -m jobcopilot score
python -m jobcopilot list
python -m jobcopilot package 1
```

## Flujo recomendado con LinkedIn

1. Entra a LinkedIn desde tu navegador normal.
2. Busca: `Junior Software Engineer`, `Backend Developer`, `Full Stack Developer`, `Product Engineer`.
3. Copia links de ofertas buenas.
4. Agrégalas:

```bash
python -m jobcopilot add-url "LINK" --company "Empresa" --role "Cargo"
python -m jobcopilot score
python -m jobcopilot package ID
```

## Archivos importantes

- `config.json`: perfil, keywords, rutas base.
- `data/jobs.json`: base local de ofertas.
- `exports/`: carpetas de postulación generadas.

## Dashboard local

Comando:

    python -m jobcopilot serve --port 8765

Abre http://127.0.0.1:8765. El flujo es human-in-the-loop: la herramienta prepara borradores y paquetes, pero no envía postulaciones automáticamente.

## Despliegue seguro en Vercel

El despliegue incluido es una versión segura/demo protegida por Basic Auth. Por seguridad, `.vercelignore` excluye `config.json`, `data/jobs.json`, `data/last_scan.json`, `exports/`, CVs, logs y tracker local.

Variables obligatorias en Vercel:

- `AUTH_USER`: usuario del login del dashboard.
- `AUTH_PASSWORD`: clave larga y única. No la guardes en el repo ni la pegues en chats.

El script asistido para desplegar es:

    powershell -ExecutionPolicy Bypass -File scripts\deploy_vercel.ps1

El escaneo real y la generación persistente de paquetes corren localmente para evitar guardar credenciales, CVs o datos personales en la nube.


## Crédito / marca

Creado por Corocul como herramienta privada de automatización laboral.
