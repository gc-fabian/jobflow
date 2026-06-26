# Sistema de plantillas CV — JobFlow

Objetivo: generar CVs más bonitos, profesionales y aptos para bots/ATS sin inventar experiencia.

## Principios

- Una página cuando sea posible.
- Sin foto, gráficos, columnas complejas ni barras de habilidad.
- Texto real seleccionable: los bots deben poder leer nombre, cargos, fechas, skills y proyectos.
- Keywords visibles según la oferta: Node.js, TypeScript, React, SQL, APIs, retail, etc.
- Exportar siempre tres formatos:
  - PDF para subir al portal.
  - TXT plano para ATS/bots.
  - MD editable para revisar rápido.
- Mantener una nota de revisión humana antes de enviar.

## Plantilla inicial

`ats-professional-v1`

Estructura:

1. Nombre + headline + contacto.
2. Perfil profesional corto.
3. Habilidades técnicas agrupadas.
4. Experiencia.
5. Proyectos relevantes.
6. Educación e idiomas.

## Reglas de adaptación

La app lee la oferta y adapta el CV:

- Si detecta Node/backend: sube Node.js y APIs en el headline.
- Si detecta TypeScript: lo agrega como keyword principal.
- Si detecta React/React Native: lo destaca en desarrollo.
- Si detecta retail/e-commerce: enfatiza Falabella Retail y plataformas internas.
- Si detecta cloud: no inventa AWS/GCP/Azure; lo deja como advertencia en `cv_review_notes.md`.
- Si detecta senior/lead/5+ años: advierte no inflar seniority.
- Si detecta inglés/presencial: lo marca para validación humana.

## Pendiente para próxima versión

- Selector visual de plantilla desde el dashboard.
- Vista previa del CV antes de exportar.
- Plantillas adicionales: `modern-ats`, `classic-latex`, `compact-tech`, `english-tech`.
- Scoring ATS por checklist: keywords encontradas, riesgos y faltantes.
