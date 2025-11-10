import json
import matplotlib.pyplot as plt
from datetime import datetime
import os

def plot_growth_graph(json_file='growth.json', output_dir='graphs'):
    """
    Reads growth data from a JSON file, plots the Instagram follower growth,
    and saves the graph as an image.

    Args:
        json_file (str): Path to the growth.json file.
        output_dir (str): Directory to save the generated graph.
    """
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found.", flush=True)
        return

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file}. Check file format.", flush=True)
        return
    except Exception as e:
        print(f"An error occurred while reading {json_file}: {e}", flush=True)
        return

    dates = []
    followers = []

    for entry in data:
        for date_str, count in entry.items():
            try:
                # Date format is dd-mm-yyyy
                dates.append(datetime.strptime(date_str, '%d-%m-%Y'))
                followers.append(count)
            except ValueError:
                print(f"Warning: Skipping invalid date format '{date_str}' in {json_file}. Expected dd-mm-yyyy.", flush=True)
                continue

    if not dates:
        print("No valid data found to plot.", flush=True)
        return

    # Sort data by date to ensure correct plotting
    sorted_data = sorted(zip(dates, followers))
    dates, followers = zip(*sorted_data)

    plt.figure(figsize=(12, 6))
    # Use a smoother line without markers for a less "pointy" appearance
    plt.plot(dates, followers, linestyle='-', color='skyblue')

    plt.title('Instagram Follower Growth')
    plt.xlabel('Date')
    plt.ylabel('Total Number of Followers')
    plt.grid(True)
    plt.tight_layout()

    # Automatically adjust x-axis ticks for better readability if many dates
    # Format x-axis dates to dd-mm-yyyy
    date_format = plt.matplotlib.dates.DateFormatter('%d-%m-%Y')
    plt.gca().xaxis.set_major_formatter(date_format)
    plt.gcf().autofmt_xdate()

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'instagram_growth_graph.png')
    plt.savefig(output_path)
    print(f"Graph saved successfully to {output_path}", flush=True)
    plt.show() # Display the graph

if __name__ == "__main__":
    plot_growth_graph()
