# Path to your JSON file
import json
data_path = "dataset.json"

# Load the JSON content from the file
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Function to count questions per level
def count_questions_per_level(data):
    """
    Counts the number of questions per proficiency level.

    Args:
        data (list): A list of dictionaries, each with a 'level' key.

    Returns:
        dict: A dictionary with levels as keys and question counts as values.
    """
    level_counts = {}

    for item in data:
        level = item.get("level")
        if level:
            level_counts[level] = level_counts.get(level, 0) + 1

    return level_counts
# data_path = "dataset_C1.json"
# Call the function and print the result
result = count_questions_per_level(data)
print(result)