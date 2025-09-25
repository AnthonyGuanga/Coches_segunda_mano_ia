# Used Cars Dataset - Exploratory Data Analysis

This repository contains a comprehensive Exploratory Data Analysis (EDA) of a used cars dataset from the Pakistani automobile market.

## Dataset Overview

The dataset contains **60,109 records** of used cars with the following key features:
- **brand**: Car brand/manufacturer
- **currency**: Price currency (PKR)
- **description**: Vehicle description
- **fuel_type**: Type of fuel (Petrol, Diesel, Hybrid, CNG, Electric)
- **item_condition**: Condition of the vehicle
- **manufacturer**: Vehicle manufacturer
- **mileage_from_odometer**: Vehicle mileage
- **model_date**: Year of the model (1942-2023)
- **price**: Vehicle price (target variable)
- **vehicle_engine**: Engine specifications
- **vehicle_transmission**: Transmission type (Manual/Automatic)

## Files Structure

### Analysis Files
- **`eda_used_cars.ipynb`** - Comprehensive Jupyter notebook with interactive analysis
- **`eda_analysis.py`** - Python script for automated EDA pipeline
- **`EDA_SUMMARY_REPORT.md`** - Detailed summary report with key findings

### Data
- **`datasets/used_car_dataset.csv`** - Original dataset (60,109 rows × 12 columns)

### Generated Files
- **`eda_visualizations.png`** - Key visualizations from the analysis

## Key Findings

### 🚗 Market Overview
- **Top Brands**: Toyota (32.9%), Suzuki (29.5%), Honda (19.0%)
- **Fuel Types**: Petrol dominates (89.6%), followed by Diesel (5.8%)
- **Transmission**: Nearly even split between Automatic (51.1%) and Manual (48.9%)

### 💰 Price Analysis
- **Average Price**: PKR 3,603,460 (~$12,945 USD)
- **Median Price**: PKR 2,300,000 (~$8,273 USD)
- **Price Range**: PKR 1,780 to PKR 210,000,000
- **Distribution**: Right-skewed with significant outliers

### 📈 Key Correlations with Price
- **Engine Size**: +0.518 (strong positive correlation)
- **Model Year**: +0.307 (moderate positive correlation)
- **Mileage**: -0.194 (weak negative correlation)

## How to Run the Analysis

### Option 1: Jupyter Notebook (Interactive)
```bash
jupyter notebook eda_used_cars.ipynb
```

### Option 2: Python Script (Automated)
```bash
python eda_analysis.py
```

### Requirements
```bash
pip install pandas numpy matplotlib seaborn
```

## Analysis Sections

1. **Data Loading and Initial Exploration**
2. **Dataset Structure Analysis**
3. **Data Summary and Unique Values**
4. **Data Cleaning and Preprocessing**
5. **Univariate Analysis**
   - Distribution of numerical variables
   - Frequency analysis of categorical variables
6. **Bivariate Analysis**
   - Price relationships with other variables
   - Correlation analysis
7. **Key Insights and Findings**

## Visualizations Generated

- Price distribution (histogram and log-scale)
- Price vs. mileage, model year, engine size (scatter plots)
- Brand and fuel type distributions
- Price distributions by categories (box plots)
- Correlation heatmap for numerical variables
- Average prices by different categories

## Market Insights

- **Pakistani Market Focus**: 100% PKR currency indicates regional dataset
- **Japanese Brand Dominance**: Toyota, Suzuki, Honda control 81.4% of market
- **Petrol Preference**: Nearly 90% of cars use petrol fuel
- **Growth Opportunities**: Electric vehicles represent only 0.1% of market
- **Price Predictors**: Engine size is the strongest predictor of price

## Data Quality

- **Excellent Coverage**: Only 85 missing values out of 780K+ data points
- **Clean Data**: Minimal preprocessing required
- **Consistent Format**: Standardized categorical variables
- **Rich Dataset**: 60K+ records provide statistical significance

## Business Applications

This analysis provides insights for:
- **Car Dealers**: Pricing strategies and inventory management
- **Market Researchers**: Understanding consumer preferences
- **Financial Institutions**: Auto loan risk assessment
- **Policy Makers**: Market regulation and environmental policies

## Future Work

- Predictive modeling for price estimation
- Time series analysis of price trends
- Geographic analysis (if location data available)
- Feature engineering for enhanced predictions

---

*Analysis completed on a dataset of 60,109 used cars from the Pakistani automobile market (1942-2023)*
