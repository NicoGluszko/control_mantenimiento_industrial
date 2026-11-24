import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

# 1. Configuración general de la página (siempre va primera)
st.set_page_config(page_title="Control de Mantenimiento", layout="wide")

st.title("Panel de Control de Mantenimiento Industrial")
st.markdown("Datos en tiempo real conectados a **SQLite (`planta_industrial.db`)**.")

if "mensaje_ok" in st.session_state:
    st.success(st.session_state.pop("mensaje_ok"))

@st.cache_data
# 2. Función para traer los datos desde SQLite
def cargar_datos():
    conn = sqlite3.connect("planta_industrial.db")
    try:
        query = """
        SELECT m.id_orden,
               m.fecha,
               e.nombre AS equipo,
               e.sector,
               e.criticidad,
               m.tipo,
               m.horas_parada,
               m.costo_usd
        FROM mantenimientos AS m
        INNER JOIN equipos AS e
          ON m.id_equipo = e.id_equipo
        ORDER BY m.fecha DESC;
        """
        return pd.read_sql(query, conn)
    finally:
        conn.close()

df = cargar_datos()

def cargar_equipos():
    conn = sqlite3.connect("planta_industrial.db")
    try:
        return pd.read_sql("SELECT id_equipo, nombre FROM equipos ORDER BY id_equipo;", conn)
    finally:
        conn.close()

def insertar_orden(id_equipo, fecha, tipo, horas_parada, costo_usd):
    conn = sqlite3.connect("planta_industrial.db")
    try:
        cursor = conn.cursor()
        # Calculamos el siguiente id_orden automáticamente
        cursor.execute("SELECT COALESCE(MAX(id_orden), 100) + 1 FROM mantenimientos;")
        nuevo_id = cursor.fetchone()[0]

        query = """
        INSERT INTO mantenimientos (id_orden, id_equipo, fecha, tipo, horas_parada, costo_usd)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        cursor.execute(query, (nuevo_id, id_equipo, fecha, tipo, horas_parada, costo_usd))
        conn.commit()  # Confirmamos el guardado en el archivo .db
    finally:
        conn.close()
        
# Permite al usuario eliminar ordenes
def eliminar_orden(id_orden):
    conn = sqlite3.connect("planta_industrial.db")
    try:
        cursor = conn.cursor()
        query = "DELETE FROM mantenimientos WHERE id_orden = ?;"
        cursor.execute(query, (int(id_orden),))
        conn.commit()
    finally:
        conn.close()
        

# Cargamos una lista de ordenes nuevas        
def insertar_lote(df_nuevo):
    conn = sqlite3.connect("planta_industrial.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id_orden), 100) FROM mantenimientos;")
        ultimo_id = cursor.fetchone()[0]

        df_a_guardar = df_nuevo.copy()
        # Generamos IDs correlativos nuevos para todo el lote
        df_a_guardar["id_orden"] = range(ultimo_id + 1, ultimo_id + 1 + len(df_a_guardar))

        # Ordenamos las columnas igual que en SQLite
        columnas = ["id_orden", "id_equipo", "fecha", "tipo", "horas_parada", "costo_usd"]
        df_a_guardar = df_a_guardar[columnas]

        # CLAVE: "append" agrega al final; "replace" te borraría todo el historial
        df_a_guardar.to_sql("mantenimientos", conn, if_exists="append", index=False)
        conn.commit()
    finally:
        conn.close()
        
        
# 3. Barra lateral (Sidebar) con filtros interactivos
st.sidebar.header("Filtros de Planta")

sectores_disponibles = df["sector"].unique().tolist()
sectores_elegidos = st.sidebar.multiselect(
    "Seleccionar Sector:",
    options=sectores_disponibles,
    default=sectores_disponibles
)

tipos_disponibles = df["tipo"].unique().tolist()
tipos_elegidos = st.sidebar.multiselect(
    "Tipo de Mantenimiento:",
    options=tipos_disponibles,
    default=tipos_disponibles
)

criticidad = df["criticidad"].unique().tolist()
criticidad_elegida = st.sidebar.multiselect(
    "Tipo de Criticidad:",
    options=criticidad,
    default=criticidad
)


# Creamos un diccionario {"Nombre del equipo": "EQ-XX"} para el selector
df_equipos = cargar_equipos()
mapa_equipos = dict(zip(df_equipos["nombre"], df_equipos["id_equipo"]))

with st.expander("Registrar nueva orden de mantenimiento"):
    with st.form("form_nueva_orden", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        equipo_nombre = c1.selectbox("Equipo:", options=list(mapa_equipos.keys()))
        fecha = c2.date_input("Fecha:", value=date.today())
        tipo = c3.selectbox("Tipo de Mantenimiento:", options=["Correctivo", "Preventivo"])

        c4, c5 = st.columns(2)
        horas_parada = c4.number_input("Horas de parada:", min_value=0.0, step=0.5)
        costo_usd = c5.number_input("Costo (USD):", min_value=0.0, step=50.0)

        enviado = st.form_submit_button("Guardar Orden en Base de Datos")

        if enviado:
            if horas_parada <= 0 or costo_usd <= 0:
                st.error("Los datos son invalidos, no pueden ser 0 o valores negativos")
            else:
                id_equipo = mapa_equipos[equipo_nombre]
                insertar_orden(
                    id_equipo=id_equipo,
                    fecha=fecha.strftime("%Y-%m-%d"),  # Mismo formato texto YYYY-MM-DD de tu base
                    tipo=tipo,
                    horas_parada=horas_parada,
                    costo_usd=costo_usd
                )
                cargar_datos.clear()  # Limpiamos la caché vieja
                st.session_state["mensaje_ok"] = f"Orden registrada correctamente para {equipo_nombre}."
                st.rerun()            # Recargamos la pantalla para ver el dato nuevo al instante

# Eliminamos una orden de mantenimiento:            
with st.expander("Eliminar una orden de mantenimiento"):
    if len(df) == 0:
        st.info("No hay órdenes cargadas para eliminar.")
    else:
        id_a_borrar = st.selectbox(
            "Seleccioná el ID de la orden a eliminar:",
            options=df["id_orden"].tolist()
        )

        # Vista previa en vivo de la orden seleccionada
        orden_preview = df[df["id_orden"] == id_a_borrar]
        st.dataframe(orden_preview, use_container_width=True, hide_index=True)

        confirmar = st.checkbox("Confirmo que quiero eliminar esta orden de forma permanente")

        if st.button("Eliminar Orden", type="primary", disabled=not confirmar):
            eliminar_orden(id_a_borrar)
            cargar_datos.clear()
            st.session_state["mensaje_ok"] = f"Orden #{id_a_borrar} eliminada correctamente."
            st.rerun()

# Agregamos ordenes desde una planilla csv
with st.expander("Importar órdenes masivas desde CSV"):
    archivo = st.file_uploader("Subí un archivo CSV con órdenes nuevas", type=["csv"])

    if archivo is not None:
        df_subido = pd.read_csv(archivo)
        st.write("Vista previa del archivo cargado:")
        st.dataframe(df_subido, use_container_width=True, hide_index=True)

        columnas_requeridas = {"id_equipo", "fecha", "tipo", "horas_parada", "costo_usd"}
        faltantes = columnas_requeridas - set(df_subido.columns)

        if faltantes:
            st.error(f"Al archivo le faltan columnas obligatorias: {', '.join(faltantes)}")
        else:
            if st.button("Confirmar e Importar a Base de Datos"):
                insertar_lote(df_subido)
                cargar_datos.clear()
                st.session_state["mensaje_ok"] = f"Ordenes cargadas correctamente."
                st.rerun()
                
        
# Aplicamos los filtros al DataFrame (puro Pandas)
df_filtrado = df[
    (df["sector"].isin(sectores_elegidos)) &
    (df["tipo"].isin(tipos_elegidos)) &
    (df["criticidad"].isin(criticidad_elegida))
]

# 4. Tarjetas de KPIs en 4 columnas
col1, col2, col3, col4 = st.columns(4)

col1.metric("Costo Total (USD)", f"${df_filtrado['costo_usd'].sum():,.0f}")
col2.metric("Horas de Parada", f"{df_filtrado['horas_parada'].sum():.1f} hs")
col3.metric("Cantidad de Órdenes", len(df_filtrado))

costo_promedio = df_filtrado['costo_usd'].mean() if len(df_filtrado) > 0 else 0
col4.metric("Costo Promedio por Orden", f"${costo_promedio:,.1f}")

st.divider()

# 5. Gráfico y Tabla lado a lado
col_izq, col_der = st.columns([1, 1.5])

with col_izq:
    st.subheader("Costo por Sector (USD)")
    resumen_sector = df_filtrado.groupby("sector")["costo_usd"].sum()
    st.bar_chart(resumen_sector)

with col_der:
    st.subheader("Detalle de Órdenes")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
# Guardar la lista de ordenes filtrada con los botones del panel izquierdo
csv_export = df_filtrado.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Descargar tabla filtrada (CSV)",
    data=csv_export,
    file_name="ordenes_mantenimiento.csv",
    mime="text/csv"
    )
    
    
# 6. Grafico agregado al final de la pagina

st.divider()
st.subheader("Horas de Parada por Equipo")
horas_equipo = df_filtrado.groupby("equipo")["horas_parada"].sum()
st.bar_chart(horas_equipo)


# Final
st.divider()
st.caption("Panel de Control de Mantenimiento Industrial | Desarrollado con Python, Streamlit y SQLite.")