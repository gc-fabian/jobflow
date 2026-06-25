# Prompt para revisar temas legales de una página/app con GPT

Copia y pega este prompt en GPT cuando quieras revisar qué temas legales debe cubrir la página de JobFlow by Corocul. Esto no reemplaza a un abogado; sirve para preparar una checklist y saber qué preguntar.

```text
Actúa como un revisor legal/product counsel para una aplicación web chilena/latam llamada "JobFlow by Corocul".

Contexto:
- Es una herramienta privada creada por Corocul para ayudar a una persona usuaria a buscar, priorizar y preparar postulaciones laborales.
- La app permite guardar links/texto de ofertas, calcular score/calce, generar borradores de correo/mensaje/checklist y marcar estados de postulación.
- NO envía postulaciones automáticamente.
- NO debe pedir ni guardar contraseñas de LinkedIn, AIRA, GetOnBoard u otros portales.
- Puede abrir búsquedas públicas o usar texto/link copiado manualmente por el usuario desde sus propias sesiones.
- En despliegue público/Vercel debe tener login y no subir datos personales locales, CVs, exports, tokens ni data/jobs.json.
- Puede mostrar marca "Creado por Corocul".
- Público objetivo inicial: uso privado/personal, no SaaS masivo todavía.

Necesito que revises qué temas legales y de compliance debo considerar para publicar una landing o dashboard privado. Responde en español claro y separa:

1. Documentos/páginas recomendadas:
   - Términos y condiciones
   - Política de privacidad
   - Política de cookies si aplica
   - Aviso de uso de IA/automatización
   - Disclaimer de no afiliación con LinkedIn/AIRA/GetOnBoard/empresas
   - Disclaimer de que no garantiza empleo ni resultados

2. Datos personales:
   - Qué datos personales se manejan
   - Qué datos no se deben guardar
   - Qué base legal/consentimiento podría aplicar
   - Cómo explicar retención y eliminación de datos
   - Qué mencionar si se usa Vercel/GitHub u otros proveedores

3. Riesgos por scraping/portales:
   - Qué evitar para no violar términos de terceros
   - Diferencia entre links/texto pegado manualmente y scraping automatizado con sesión
   - Recomendaciones para LinkedIn y portales de empleo

4. Propiedad intelectual y marca:
   - Cómo indicar "Creado por Corocul"
   - Cómo evitar parecer afiliado a portales o empresas
   - Qué revisar si uso logos/nombres de empresas

5. Seguridad:
   - Recomendaciones de login
   - Manejo de tokens/secretos
   - Qué no subir a GitHub
   - Cómo informar límites del sistema

6. Checklist práctica antes de publicar:
   - Debe ser accionable, priorizada por riesgo: alto/medio/bajo.

7. Borradores base:
   - Redacta un borrador corto de footer legal.
   - Redacta un borrador corto de aviso de privacidad para uso privado.
   - Redacta un borrador de disclaimer de automatización/no envío automático.

No inventes normativa específica si no estás seguro. Si mencionas leyes chilenas o internacionales, marca qué debe validar un abogado.
```
