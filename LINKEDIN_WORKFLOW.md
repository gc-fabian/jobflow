# Workflow LinkedIn para Fabián

## Lo que puedo automatizar sin tu clave

- Guardar links de ofertas.
- Extraer texto público cuando la página lo permite.
- Puntuar calce según tu perfil.
- Generar carpeta de postulación.
- Copiar CV base.
- Crear correo, texto de formulario y checklist.
- Mantener tracker local.

## Lo que requiere tu acceso

LinkedIn normalmente bloquea extracción completa si no hay sesión iniciada. Para búsqueda personalizada hay dos opciones:

### Opción A — Segura y rápida
1. Tú abres LinkedIn con tu cuenta.
2. Buscas ofertas.
3. Copias links buenos.
4. Los agregamos con:

```bash
python -m jobcopilot add-url "LINK" --company "EMPRESA" --role "CARGO"
python -m jobcopilot score
python -m jobcopilot package ID
```

### Opción B — Automatización con navegador logueado
Requiere que tú inicies sesión manualmente en un perfil de navegador local. El sistema podría leer páginas que tú abras, pero no debería enviar postulaciones automáticamente.

Regla: siempre revisión humana antes de postular.

## Búsquedas recomendadas

- Junior Software Engineer Chile
- Backend Developer Junior Chile
- Full Stack Developer Junior Chile
- Product Engineer Junior Chile
- Python Developer Junior Chile
- Node.js Developer Chile
- Software Engineer AI Chile
