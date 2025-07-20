import csv

def estimate_costs(file_path):
    total = 0.0
    with open(file_path, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hours = float(row['UsageHours'])
            rate = float(row['HourlyRate'])
            cost = hours * rate
            total += cost
            print(f"Resource: {row['ResourceName']}, Cost: ${cost:.2f}")
    print(f"\nTotal Estimated Cost: ${total:.2f}")

if __name__ == "__main__":
    estimate_costs('resources.csv')
