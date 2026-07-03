# Handoff: Radar Inmobiliario Galicia — Sara Álvarez Inmobiliaria

## Overview
Herramienta interna para una inmobiliaria de Pontevedra (Sara Álvarez Inmobiliaria, saraalvarezinmobiliaria.com). Objetivo: que la propietaria vea en un mapa todas las propiedades en venta/alquiler de la zona (Pontevedra, Vigo, Bueu, Rías Baixas), detecte **anuncios nuevos de particulares** para captarlos, y reciba avisos automáticos — sin buscar a mano en los portales.

El sistema tiene dos partes:
1. **Frontend** (diseñado — ver archivo adjunto): mapa interactivo + panel "Radar de captación".
2. **Backend "vigilante"** (a implementar): proceso programado que consulta fuentes de anuncios, detecta novedades y actualiza los datos + envía avisos.

## About the Design Files
`Mapa Propiedades Galicia.dc.html` es una **referencia de diseño en HTML** (prototipo funcional con datos de ejemplo), no código de producción. La tarea es **recrear este diseño** en el stack que se elija. No hay codebase existente: elige el framework más apropiado (sugerencia: Next.js o Vite+React, Leaflet para el mapa, SQLite/Postgres para datos, y un cron/scheduled job para el vigilante — puede ser un GitHub Action, un cron en un VPS, o un worker de Cloudflare/Vercel).

## Fidelity
**High-fidelity** para el frontend: colores, tipografía, espaciados y comportamiento están definidos y deben recrearse fielmente. El backend está especificado a nivel funcional (baja fidelidad — decisiones técnicas libres).

## Screens / Views

### 1. Cabecera
- Barra superior, fondo `#12332e`, texto `#f5f4f1`, padding 12px 20px.
- Izquierda: título "Radar Inmobiliario · Galicia" (Libre Franklin 800, 17px) + subtítulo 12px opacidad 0.75.
- Derecha: filtros como chips redondeados (border-radius 999px, 13px, weight 600): **Todos / Venta / Alquiler / Sara Álvarez**. Chip activo: fondo claro `#f5f4f1`, texto `#12332e`; inactivo: transparente con borde `rgba(255,255,255,0.35)`.
- Contador "N propiedades" en pill con fondo `rgba(255,255,255,0.12)`.

### 2. Mapa (área principal)
- Leaflet, tiles CARTO light (`light_all`), centrado en Pontevedra `[42.4318, -8.6446]`, zoom 12.
- **Pines = pills de precio**: fondo del color según tipo, texto blanco 12px/700, borde blanco 2px, sombra `0 2px 6px rgba(0,0,0,0.3)`, hover scale 1.08. Pin seleccionado: fondo `#111`.
- Colores por tipo: Venta `#12332e` · Alquiler `#1e6fb8` · Inmuebles propios de la agencia `#c2572a`.
- Leyenda flotante arriba-derecha (fondo blanco 95%, borde `#e2e0da`, radius 10px).
- Toggle (tweak): mostrar precio en el pin o solo punto de color.

### 3. Ficha de propiedad (card flotante abajo-izquierda al pinchar un pin)
- 320px ancho, fondo blanco, radius 14px, sombra `0 8px 32px rgba(18,51,46,0.28)`, animación de entrada 0.18s (fade + translateY 12px).
- Foto 170px de alto (cover) con badge del tipo (uppercase, 11px/700) y botón cerrar (círculo 30px, fondo `rgba(0,0,0,0.55)`).
- Contenido: precio (22px/800, `#12332e`) + specs a la derecha (12px `#777`) · título (14px/600) · dirección (13px `#666`).
- Chips de detalles (12px/600, fondo `#f0efe9`, pill, `white-space: nowrap`): 🏠 tipo de vivienda · 🧭 orientación.
- Botón-enlace "Ver en {fuente} →" (fondo `#f0efe9`, hover `#e6e4db`) con punto de color de la fuente; abre el anuncio original en pestaña nueva.

### 4. Panel "Radar de captación" (aside derecho, 300px)
- Fondo blanco, borde izquierdo `#e2e0da`.
- Cabecera: punto naranja pulsante + "Radar de captación" (14px/800) + subtítulo "Anuncios de particulares recientes — para llamar y captar".
- Lista scrolleable de anuncios de **particulares**, ordenados por fecha (más nuevo arriba), máx. 15:
  - "NUEVO HOY" / "AYER" / "HACE N DÍAS" en naranja `#c2572a` uppercase 11px/700 + fuente a la derecha en gris.
  - Título 13px/600 · dirección 12px `#777` · precio 13px/800 alineado derecha.
  - Click → selecciona la propiedad en el mapa y hace `setView` a su posición (zoom 13). Ítem seleccionado: fondo `#f5efe9`. Hover: `#faf9f5`.

## Interactions & Behavior
- Click en pin → abre ficha + `panTo` a la propiedad.
- Cambiar filtro → re-renderiza pines, cierra ficha.
- Los enlaces "Ver en..." apuntan SIEMPRE al anuncio original (Idealista, Fotocasa, web de la inmobiliaria...).
- Responsive: en móvil el aside del radar debería pasar a ser un bottom-sheet o pestaña (no diseñado — decidir en implementación).

## Backend "vigilante" (a implementar — especificación funcional)

### Fuentes de datos (por orden de prioridad)
1. **API oficial de Idealista** — solicitar acceso gratuito en developers.idealista.com (límite ~100 peticiones/mes en el tier gratuito; valorar tier de pago si se queda corto). Buscar por provincia de Pontevedra, venta y alquiler, ordenado por fecha de publicación.
2. **Webs de inmobiliarias locales** con permiso o datos públicos, p. ej. Inmobiliaria Freire (freireinmobiliaria.com, Bueu) — revisar términos de uso antes de automatizar; alternativa: revisión manual asistida.
3. **La propia web de la agencia** (saraalvarezinmobiliaria.com, motor ClickViviendas) para los inmuebles propios.

### Restricciones legales (IMPORTANTE)
- NO hacer scraping de portales que lo prohíben (Idealista/Fotocasa bloquean bots; usar solo sus APIs oficiales o servicios de datos licenciados).
- NO almacenar datos personales de propietarios (teléfonos, nombres) extraídos automáticamente — RGPD. El flujo correcto: la herramienta muestra el enlace al anuncio y la usuaria contacta manualmente.
- Idealista oculta la ubicación exacta en muchos anuncios: usar las coordenadas aproximadas que da la API y marcarlas como "zona aproximada" en el mapa (p. ej. círculo en vez de pin).

### Lógica del vigilante
- Job programado cada 6–12 h (cron).
- Para cada fuente: obtener anuncios → normalizar al modelo de datos → comparar contra la BD por ID/URL → los no vistos se marcan `nuevo` con timestamp.
- Detectar si el anunciante es **particular vs agencia** (la API de Idealista lo indica) — los particulares alimentan el Radar de captación.
- Avisos: al detectar novedades de particulares en las zonas configuradas, enviar resumen por **WhatsApp** (API de WhatsApp Business / Twilio) o email: "🔔 Nuevo piso de particular en Sanxenxo, 2 hab, 180.000 € — [enlace]".
- Zonas prioritarias configurables: Pontevedra centro y afueras (A Caeira, Marcón, Bora, Xeve...), Sanxenxo, Marín, Poio, Bueu/Cela/Beluso, Vigo.

### Modelo de datos (propiedad)
```
id, source (idealista|fotocasa|freire|agencia|...), source_url,
type (venta|alquiler), price (null = consultar), currency,
lat, lng, location_precision (exact|approx),
title, address, municipality, ptype (piso|casa|chalet|...),
rooms, baths, m2, orientation (nullable),
owner_kind (particular|agencia), photo_url,
first_seen_at, last_seen_at, is_new (bool)
```

## State Management (frontend)
- `type` (filtro activo), `selId` (propiedad seleccionada), datos de propiedades (fetch a la API propia del backend, refresco periódico o SSE/websocket para "en vivo").
- El mapa Leaflet se instancia una vez; los markers se re-renderizan al cambiar filtro/selección.

## Design Tokens
- **Tipografía**: Libre Franklin (Google Fonts), weights 400–800. Título 17px/800 · precio card 22px/800 · cuerpo 13-14px · metadatos 11-12px.
- **Colores**: verde oscuro `#12332e` (primario/venta) · azul `#1e6fb8` (alquiler) · naranja `#c2572a` (agencia/novedades) · granate `#7a2b3a` (Freire) · fondo `#f5f4f1` · superficie `#ffffff` · chips `#f0efe9` · bordes `#e2e0da`/`#f2f0ea` · textos `#222`/`#666`/`#777`/`#888`.
- Colores de fuente: Idealista `#b8c400` · Fotocasa `#0046fe` · Wallapop `#13c1ac` · Milanuncios `#f0524c`.
- **Radios**: pills 999px · cards 14px · leyenda 10px · botón-enlace 10px.
- **Sombras**: card `0 8px 32px rgba(18,51,46,0.28)` · leyenda `0 2px 10px rgba(18,51,46,0.12)` · pin `0 2px 6px rgba(0,0,0,0.3)`.

## Assets
- Tiles de mapa: CARTO basemaps (`https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`, atribución OpenStreetMap + CARTO).
- Fotos del prototipo: placeholders de picsum.photos — en producción usar las fotos del anuncio original (la API de Idealista las incluye).
- Leaflet 1.9.4 (CDN unpkg).

## Files
- `Mapa Propiedades Galicia.dc.html` — prototipo completo (mapa + ficha + radar + filtros). Los datos de ejemplo y el generador de datos demo están en el bloque `<script>` final; en producción se sustituyen por el fetch a la API propia.

## Datos reales ya identificados
- **Sara Álvarez Inmobiliaria**: 6 inmuebles destacados con URLs reales en el array `AGENCIA` del prototipo (Moraña, Pontevedra, Sanxenxo, Mourente, Marín) — la web usa el motor ClickViviendas.
- **Inmobiliaria Freire (Bueu)**: 7 anuncios reales en el array `FREIRE` (Meiro, A Graña, As Meanes, centro de Bueu, Montemogos-Beluso, Bon de Abaixo, Banda do Río), precios "Consultar". Tel. 986 320 448.
