# Panel de Control de Mantenimiento Industrial

**[Abrir aplicación en vivo](https://tu-link-real.streamlit.app)**

Aplicación web interactiva construida con **Python, Streamlit, Pandas y SQLite** para el seguimiento de órdenes de mantenimiento en planta.

## Funcionalidades principales
- Filtros cruzados en tiempo real por sector, tipo de mantenimiento y criticidad.
- KPIs gerenciales (costo total, horas de parada, cantidad de órdenes y costo promedio protegido contra valores vacíos).
- Operación CRUD sobre SQLite: alta de nuevas órdenes con validación, borrado seguro con vista previa y confirmación.
- Carga masiva de órdenes desde archivos CSV (con verificación de columnas) y exportación de tablas filtradas.