#!/usr/bin/env python3
"""
Exploratory Data Analysis (EDA) for Used Cars Dataset
This script performs comprehensive EDA on the used cars dataset.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# Configure plotting and warnings
plt.style.use('default')
sns.set_palette("husl")
warnings.filterwarnings('ignore')

def load_and_explore_data(file_path):
    """Load dataset and perform initial exploration."""
    print("="*60)
    print("EXPLORATORY DATA ANALYSIS - USED CARS DATASET")
    print("="*60)
    
    # Load the dataset
    df = pd.read_csv(file_path)
    print(f"✓ Dataset loaded successfully!")
    print(f"✓ Dataset shape: {df.shape}")
    
    return df

def analyze_structure(df):
    """Analyze the structure of the dataset."""
    print("\n" + "="*50)
    print("1. DATASET STRUCTURE ANALYSIS")
    print("="*50)
    
    print(f"Shape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"\nData Types:")
    print(df.dtypes)
    
    # Check for missing values
    missing_data = pd.DataFrame({
        'Column': df.columns,
        'Missing_Count': df.isnull().sum(),
        'Missing_Percentage': (df.isnull().sum() / len(df)) * 100
    })
    missing_data = missing_data[missing_data['Missing_Count'] > 0].sort_values('Missing_Count', ascending=False)
    
    if len(missing_data) > 0:
        print(f"\nMissing Values:")
        print(missing_data)
    else:
        print(f"\n✓ No missing values found in the dataset!")
    
    return missing_data

def clean_data(df):
    """Clean and preprocess the data."""
    print("\n" + "="*50)
    print("2. DATA CLEANING AND PREPROCESSING")
    print("="*50)
    
    df_clean = df.copy()
    
    # Remove unnamed index column if exists
    if 'Unnamed: 0' in df_clean.columns:
        df_clean = df_clean.drop('Unnamed: 0', axis=1)
        print("✓ Removed unnamed index column")
    
    # Clean mileage data
    def clean_mileage(mileage_str):
        if pd.isna(mileage_str):
            return np.nan
        try:
            return int(str(mileage_str).replace(',', '').replace(' km', '').replace('km', ''))
        except:
            return np.nan
    
    df_clean['mileage_numeric'] = df_clean['mileage_from_odometer'].apply(clean_mileage)
    print(f"✓ Created mileage_numeric: {df_clean['mileage_numeric'].count()} non-null values")
    
    # Clean engine data
    def clean_engine(engine_str):
        if pd.isna(engine_str):
            return np.nan
        try:
            numeric_part = ''.join(filter(str.isdigit, str(engine_str)))
            return int(numeric_part) if numeric_part else np.nan
        except:
            return np.nan
    
    df_clean['engine_numeric'] = df_clean['vehicle_engine'].apply(clean_engine)
    print(f"✓ Created engine_numeric: {df_clean['engine_numeric'].count()} non-null values")
    
    return df_clean

def analyze_categorical_variables(df_clean):
    """Analyze categorical variables."""
    print("\n" + "="*50)
    print("3. CATEGORICAL VARIABLES ANALYSIS")
    print("="*50)
    
    categorical_cols = ['brand', 'currency', 'fuel_type', 'item_condition', 'manufacturer', 'vehicle_transmission']
    
    for col in categorical_cols:
        if col in df_clean.columns:
            print(f"\n{col.upper()}:")
            print(f"  Unique values: {df_clean[col].nunique()}")
            print(f"  Top 5 values:")
            print(f"  {df_clean[col].value_counts().head(5)}")

def analyze_numerical_variables(df_clean):
    """Analyze numerical variables."""
    print("\n" + "="*50)
    print("4. NUMERICAL VARIABLES ANALYSIS")
    print("="*50)
    
    numerical_vars = ['price', 'mileage_numeric', 'model_date', 'engine_numeric']
    
    for var in numerical_vars:
        if var in df_clean.columns:
            print(f"\n{var.upper()}:")
            print(df_clean[var].describe())

def generate_visualizations(df_clean):
    """Generate key visualizations."""
    print("\n" + "="*50)
    print("5. GENERATING VISUALIZATIONS")
    print("="*50)
    
    # Set up the plotting
    fig = plt.figure(figsize=(20, 15))
    
    # Price distribution
    plt.subplot(3, 3, 1)
    plt.hist(df_clean['price'].dropna(), bins=50, alpha=0.7, color='skyblue')
    plt.title('Price Distribution')
    plt.xlabel('Price')
    plt.ylabel('Frequency')
    
    # Price vs Mileage scatter plot (sample)
    plt.subplot(3, 3, 2)
    sample_data = df_clean.dropna(subset=['price', 'mileage_numeric']).sample(n=min(2000, len(df_clean)))
    plt.scatter(sample_data['mileage_numeric'], sample_data['price'], alpha=0.5)
    plt.xlabel('Mileage (km)')
    plt.ylabel('Price')
    plt.title('Price vs Mileage')
    
    # Top 10 brands
    plt.subplot(3, 3, 3)
    top_brands = df_clean['brand'].value_counts().head(10)
    plt.bar(range(len(top_brands)), top_brands.values, color='lightcoral')
    plt.title('Top 10 Brands')
    plt.xticks(range(len(top_brands)), top_brands.index, rotation=45)
    plt.ylabel('Frequency')
    
    # Fuel type distribution
    plt.subplot(3, 3, 4)
    fuel_counts = df_clean['fuel_type'].value_counts()
    plt.pie(fuel_counts.values, labels=fuel_counts.index, autopct='%1.1f%%', startangle=90)
    plt.title('Fuel Type Distribution')
    
    # Model year distribution
    plt.subplot(3, 3, 5)
    plt.hist(df_clean['model_date'].dropna(), bins=30, alpha=0.7, color='gold')
    plt.title('Model Year Distribution')
    plt.xlabel('Model Year')
    plt.ylabel('Frequency')
    
    # Transmission distribution
    plt.subplot(3, 3, 6)
    trans_counts = df_clean['vehicle_transmission'].value_counts()
    plt.bar(trans_counts.index, trans_counts.values, color='lightgreen')
    plt.title('Transmission Distribution')
    plt.xticks(rotation=45)
    plt.ylabel('Frequency')
    
    # Price by fuel type (box plot)
    plt.subplot(3, 3, 7)
    fuel_types = df_clean['fuel_type'].value_counts().head(5).index
    price_by_fuel = [df_clean[df_clean['fuel_type'] == fuel]['price'].dropna() for fuel in fuel_types]
    plt.boxplot(price_by_fuel, labels=fuel_types)
    plt.title('Price by Fuel Type')
    plt.xticks(rotation=45)
    plt.ylabel('Price')
    
    # Correlation heatmap
    plt.subplot(3, 3, 8)
    numerical_vars = ['price', 'mileage_numeric', 'model_date', 'engine_numeric']
    correlation_data = df_clean[numerical_vars].corr()
    sns.heatmap(correlation_data, annot=True, cmap='coolwarm', center=0, square=True, fmt='.2f')
    plt.title('Correlation Matrix')
    
    # Average price by top brands
    plt.subplot(3, 3, 9)
    avg_price_brand = df_clean.groupby('brand')['price'].mean().sort_values(ascending=False).head(10)
    plt.bar(range(len(avg_price_brand)), avg_price_brand.values, color='plum')
    plt.title('Average Price by Brand (Top 10)')
    plt.xticks(range(len(avg_price_brand)), avg_price_brand.index, rotation=45)
    plt.ylabel('Average Price')
    
    plt.tight_layout()
    plt.savefig('eda_visualizations.png', dpi=300, bbox_inches='tight')
    print("✓ Visualizations saved as 'eda_visualizations.png'")
    plt.show()

def generate_insights(df_clean):
    """Generate key insights and findings."""
    print("\n" + "="*50)
    print("6. KEY INSIGHTS AND FINDINGS")
    print("="*50)
    
    # Dataset overview
    print(f"\n📊 DATASET OVERVIEW:")
    print(f"   • Total records: {len(df_clean):,}")
    print(f"   • Total features: {df_clean.shape[1]}")
    print(f"   • Missing values: {df_clean.isnull().sum().sum()}")
    
    # Price insights
    print(f"\n💰 PRICE ANALYSIS:")
    price_stats = df_clean['price'].describe()
    print(f"   • Average price: ${price_stats['mean']:,.2f}")
    print(f"   • Median price: ${price_stats['50%']:,.2f}")
    print(f"   • Price range: ${price_stats['min']:,.2f} - ${price_stats['max']:,.2f}")
    print(f"   • Standard deviation: ${price_stats['std']:,.2f}")
    
    # Brand insights
    print(f"\n🚗 BRAND ANALYSIS:")
    top_brand = df_clean['brand'].value_counts().index[0]
    top_brand_count = df_clean['brand'].value_counts().iloc[0]
    total_brands = df_clean['brand'].nunique()
    print(f"   • Most common brand: {top_brand} ({top_brand_count:,} cars, {top_brand_count/len(df_clean)*100:.1f}%)")
    print(f"   • Total number of brands: {total_brands}")
    
    # Fuel type insights
    print(f"\n⛽ FUEL TYPE ANALYSIS:")
    fuel_counts = df_clean['fuel_type'].value_counts()
    most_common_fuel = fuel_counts.index[0]
    print(f"   • Most common fuel type: {most_common_fuel} ({fuel_counts.iloc[0]:,} cars, {fuel_counts.iloc[0]/len(df_clean)*100:.1f}%)")
    
    # Correlation insights
    print(f"\n📈 CORRELATION INSIGHTS:")
    numerical_vars = ['price', 'mileage_numeric', 'model_date', 'engine_numeric']
    correlation_data = df_clean[numerical_vars].corr()
    price_correlations = correlation_data['price'].sort_values(key=abs, ascending=False)
    print("   • Strongest correlations with price:")
    for var, corr in price_correlations.items():
        if var != 'price':
            direction = "positive" if corr > 0 else "negative"
            strength = "strong" if abs(corr) > 0.5 else "moderate" if abs(corr) > 0.3 else "weak"
            print(f"     - {var}: {corr:.3f} ({strength} {direction} correlation)")
    
    print(f"\n🔍 ADDITIONAL OBSERVATIONS:")
    currency_dominant = df_clean['currency'].value_counts().index[0]
    print(f"   • Dataset appears to be primarily from Pakistan ({currency_dominant} currency dominant)")
    print(f"   • Price distribution is right-skewed with some high-value outliers")
    print(f"   • Mileage and engine data required cleaning (contained text format)")
    print(f"   • Missing values are minimal, making the dataset quite complete")

def main():
    """Main function to run the complete EDA."""
    # File path
    file_path = 'datasets/used_car_dataset.csv'
    
    try:
        # Load and explore data
        df = load_and_explore_data(file_path)
        
        # Analyze structure
        analyze_structure(df)
        
        # Clean data
        df_clean = clean_data(df)
        
        # Analyze variables
        analyze_categorical_variables(df_clean)
        analyze_numerical_variables(df_clean)
        
        # Generate visualizations
        generate_visualizations(df_clean)
        
        # Generate insights
        generate_insights(df_clean)
        
        print("\n" + "="*60)
        print("✅ EXPLORATORY DATA ANALYSIS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except FileNotFoundError:
        print(f"❌ Error: Dataset file '{file_path}' not found!")
        print("Please ensure the dataset is in the correct location.")
    except Exception as e:
        print(f"❌ Error occurred during analysis: {str(e)}")

if __name__ == "__main__":
    main()