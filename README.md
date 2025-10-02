# Predicción de Precios de Coches de Segunda Mano

## Introducción
En este proyecto hemos desarrollado un modelo de **machine learning** para predecir el precio de venta de coches de segunda mano. Nuestro objetivo ha sido construir un flujo completo desde la exploración de datos hasta la generación de predicciones, permitiendo comprender qué factores influyen más en el precio de los vehículos.

---

## Elección del Dataset
Para nuestro trabajo, hemos utilizado el dataset `Cars_Data_6k.csv`, que contiene aproximadamente 6.000 registros de coches con las siguientes variables:

- `Year`: Año del coche  
- `Present_Price`: Precio original del coche  
- `Kms_Driven`: Kilómetros recorridos  
- `Fuel_Type`: Tipo de combustible  
- `Seller_Type`: Tipo de vendedor  
- `Transmission`: Tipo de transmisión  
- `Owner`: Número de propietarios anteriores  
- `Selling_Price`: Precio de venta (variable objetivo)  

**Motivación:** Elegimos este dataset porque contiene información suficiente para construir un modelo de regresión robusto y permite explorar cómo diferentes características de un coche afectan a su precio. Además, su tamaño es adecuado para entrenar modelos de machine learning sin requerir recursos computacionales elevados.

---

## Definición del Problema
Queremos responder a la pregunta:  
**“¿Cuál será el precio de venta de un coche de segunda mano dado sus características?”**

- Tipo de problema: **Regresión**, ya que la variable objetivo (`Selling_Price`) es continua.  
- Variables explicativas: todas las columnas excepto `Selling_Price`.  
- Variable dependiente: `Selling_Price`.

---

## Exploración de Datos (EDA)
Durante la exploración inicial:

- Se analizaron estadísticas descriptivas de todas las variables.  
- Se visualizó la distribución de los precios y los kilómetros recorridos.  
- Se identificaron outliers en `Kms_Driven` y `Present_Price`.  
- Se examinó la relación entre variables categóricas (`Fuel_Type`, `Seller_Type`, `Transmission`) y el precio de venta mediante gráficos de caja y correlaciones.

---

## Preprocesamiento
Antes de entrenar los modelos:

- Se eliminaron valores nulos y registros duplicados.  
- Las variables categóricas (`Fuel_Type`, `Seller_Type`, `Transmission`) fueron codificadas usando **One-Hot Encoding**.  
- Se normalizaron las variables numéricas para mejorar la convergencia del modelo.  
- Se dividió el dataset en **80% entrenamiento y 20% prueba**.

---

## Entrenamiento de Modelos
Entrenamos y evaluamos varios modelos de regresión:

1. **Regresión Lineal**
   - Hiperparámetros: predeterminados (`fit_intercept=True`)  
   - Permite una interpretación directa de la influencia de cada variable sobre el precio.

2. **Random Forest Regressor**
   - Hiperparámetros: `n_estimators=100`, `max_depth=10`, `random_state=42`  
   - Captura relaciones no lineales entre variables y precio.  

---

## Evaluación del Modelo
Métricas utilizadas:

- **MAE (Mean Absolute Error)**  
- **RMSE (Root Mean Squared Error)**  
- **R² (Coeficiente de determinación)**

**Resultados destacados:**

- El **Random Forest** presentó mejor desempeño que la regresión lineal, mostrando menor error medio y mayor R².  
- Las variables que más influyen en el precio son `Present_Price`, `Kms_Driven` y `Year`.  
- El modelo captura la tendencia general, aunque los coches con precios extremadamente altos o bajos presentan errores mayores.

---

## Conclusiones
- El proyecto permite predecir precios de coches de segunda mano de manera razonablemente precisa.  
- Las características más relevantes para la predicción son el precio original, los kilómetros recorridos y el año del vehículo.  
- Posibles mejoras: ampliar el dataset con más coches, probar modelos avanzados como XGBoost, y realizar ingeniería de características adicional (por ejemplo, antigüedad del coche, mercado de segunda mano por región).  

---

