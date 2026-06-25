# Usuario candidato sensibilizado — JobFlow by Corocul

## Qué es

El “usuario candidato sensibilizado” es el perfil que JobFlow usa para buscar trabajo como si conociera al candidato: sus objetivos, habilidades reales, límites, evidencia de proyectos, preferencias y preguntas pendientes.

No es un perfil ficticio para inventar experiencia. Es una representación operativa del candidato para orientar búsqueda, scoring y preparación de postulaciones.

## Para qué sirve

1. Buscar mejor
   - Genera búsquedas por rol, tecnología, ubicación y empresa.
   - Separa portales públicos de portales con login manual.
   - Evita depender solo de una búsqueda genérica.

2. Puntuar mejor
   - Sube score cuando la oferta calza con roles objetivo, skills y modalidad.
   - Baja score o marca riesgo cuando aparece seniority alto, lead/head/manager o 5+ años.
   - Mantiene trazabilidad de razones y brechas.

3. Preparar postulaciones honestas
   - Usa evidencia real del candidato.
   - No inventa certificaciones, seniority, empresas ni años.
   - Deja `[COMPLETAR]` cuando falta renta, disponibilidad, CV o motivación específica.

4. Mostrar debug al usuario
   - Permite explicar “por qué esta oferta llegó” y “por qué esta no”.

## Campos principales

- `headline`: posicionamiento breve del candidato.
- `target_roles`: roles objetivo.
- `seniority_target`: nivel esperado.
- `preferred_work_modes`: remoto/híbrido/presencial y zonas.
- `locations`: ubicaciones aceptadas.
- `skills_core`: habilidades fuertes para scoring.
- `skills_plus`: diferenciales que ayudan a destacar.
- `skills_learning`: brechas aceptables si el rol lo permite.
- `evidence_projects`: evidencia real para cartas/formularios.
- `deal_breakers`: señales que no deberían priorizarse.
- `search_queries`: búsquedas sugeridas por perfil.
- `application_voice`: tono de postulación.
- `missing_data_questions`: preguntas que la app debe recordar antes de enviar.

## Flujo diseñado

1. El usuario define o ajusta el perfil en “Usuario candidato”.
2. La app guarda el perfil en `config.json` local.
3. Al escanear, el scanner usa keywords/roles/empresas objetivo.
4. Al puntuar, `score_job()` compara la oferta con el perfil.
5. Al preparar una postulación, los textos usan el headline, skills y evidencia real.
6. El debug muestra decisiones tomadas por la app.

## Regla de seguridad

El perfil puede tener datos personales en local, por eso `config.json` está ignorado por Git. En GitHub solo va `config.example.json` con placeholders.

## Regla humana

JobFlow prepara y recomienda; no envía postulaciones automáticamente.
