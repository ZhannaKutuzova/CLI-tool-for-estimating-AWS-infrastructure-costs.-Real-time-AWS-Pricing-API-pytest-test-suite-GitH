# Cloud Cost Estimator 💸

A simple Python script that estimates cloud infrastructure costs from a CSV file.  
This is a mock project created for learning purposes — it does not connect to AWS or any real cloud provider.

## 📁 Files
- `cost_calculator.py` – the Python script that performs the calculations
- `resources.csv` – a sample CSV file with usage data

## 📊 Sample CSV Format
```csv
ResourceName,UsageHours,HourlyRate
EC2 Instance,50,0.024
RDS Database,100,0.1
S3 Storage,20,0.005
