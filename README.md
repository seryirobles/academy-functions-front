# Azure Function Web Client (Flask)

Pequeña app web con un campo de texto y botón **Submit**. Llama a tu Azure Function
(`http_trigger`) pasando `name` y muestra la respuesta.

## 1) Configura la URL
Copia `.env.example` a `.env` y pon tu `FUNCTION_URL` completo (incluye `?code=...`).

## 2) Instala dependencias
uv sync