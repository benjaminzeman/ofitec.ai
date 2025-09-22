# Utilidades RUT (backend/utils/chile.py)

Normalización y validación centralizadas del Rol Único Tributario (RUT) chileno.

## Objetivos

- Evitar múltiples implementaciones parciales / inconsistentes.
- Facilitar endurecimiento de validaciones y métricas de calidad.
- Proveer una API mínima, estable y testeable.

## Funciones Exportadas

| Función | Firma | Retorno | Descripción |
|---------|-------|---------|-------------|
| `rut_normalize` | `(val: Optional[str])` | `str / None` | Limpia puntos/espacios, upper DV, valida forma básica y retorna `########-D`. Devuelve `None` si input vacío o inválido. |
| `rut_is_valid` | `(val: Optional[str])` | `bool` | Aplica algoritmo módulo 11 sobre cuerpo y DV. `True` sólo si el DV calculado coincide. |

## Algoritmo de DV (Resumen)

1. Separar cuerpo y dígito verificador (DV) por `-`.
2. Recorrer el cuerpo numérico desde derecha a izquierda multiplicando por la secuencia cíclica 2..7.
3. Sumar productos; calcular `11 - (suma % 11)`.
4. Mapear: `11 -> 0`, `10 -> K`, otro -> dígito.
5. Comparar con DV entregado (normalizado a mayúscula).

## Ejemplos

| Input | `rut_normalize` | `rut_is_valid` |
|-------|-----------------|----------------|
| `12.345.678-5` | `12345678-5` | depende (ejemplo ilustrativo) |
| `12.345.678-k` | `12345678-K` | idem |
| `0012345678-5` | `12345678-5` | idem |
| `12345678` | `None` | `False` |
| `abc` | `None` | `False` |
| `12.345.678-0` | `12345678-0` | según cálculo |

Nota: Los ejemplos de validez dependen del DV real para el cuerpo; se recomienda probar casos conocidos en tests.

## Casos Borde / Edge Cases

- Cadenas vacías o sólo whitespace → `None`.
- Múltiples guiones (`12--3-4`) → se rechaza (`None`).
- DV inválido (no `[0-9kK]`) → `None`.
- Cuerpo con caracteres no numéricos → `None`.
- Cuerpo con longitud > 9 (sin justificación) → se podría rechazar en versiones futuras; hoy sólo se limpia.
- DV `K` se devuelve siempre en mayúscula.

## Diferencia con Fallback Interno

`backend/server.py` incluye un helper `_rut_normalize` que intenta importar esta función; si falla (deploy parcial) aplica un fallback simplificado (strip + upper DV) **sin** validar el DV. Debes migrar cualquier script que todavía tenga su propia versión a importar desde `backend.utils.chile`.

## Uso Recomendado

```python
from backend.utils.chile import rut_normalize, rut_is_valid

rut = rut_normalize(user_input)
if rut and rut_is_valid(rut):
    # Persistir o usar en lógica de negocio
    ...
else:
    # Manejar RUT faltante o inválido
    ...
```

## Errores y Estrategia de Evolución

- La librería NO lanza excepciones por inputs inválidos; retorna `None` / `False` para mantener simplicidad.
- Futuro: introducir `TypedDict` o `dataclass` si se anexan metadatos (ej: cuerpo, dv, formateo original).
- Podría añadirse `rut_format_pretty("12345678-K") -> "12.345.678-K"` para UI.

## Testing Sugerido

Crear `backend/tests/test_rut_utils.py` (futuro) con casos:

- Normalización idempotente.
- DV correcto vs incorrecto.
- Inputs con puntos, espacios, letras extrañas.
- Vector de 5-10 RUTs conocidos correctos (incluyendo DV `K`).

## Métricas Futuras (Ideas)

- Contador de RUT inválidos recibidos por endpoint crítico.
- Distribución de longitud de cuerpo (sanity data).
- Porcentaje de normalizaciones que cambian el input (nivel de ruido en fuente).

## Licencia / Dominio Público

El algoritmo módulo 11 es de dominio público; la implementación aquí es trivial y puede copiarse adaptando a tus necesidades.
