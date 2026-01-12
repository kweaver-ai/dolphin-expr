import yaml
import os
import ast
from pathlib import Path
from DolphinLanguageSDK.ontology.datasource.sql import DataSourceSqlite

# Load global config using relative path from current script location
script_dir = Path(__file__).parent.absolute()
# script is in: experiments/benchmark/data/bird_dev/
# we need to go to: experiments/design/bird_baseline/config/
project_root = (
    script_dir.parent.parent.parent.parent
)  # Go up to project root (dolphin-language/)
global_config_path = (
    project_root / "experiments" / "design" / "bird_baseline" / "config" / "global.yaml"
)

with open(global_config_path, "r") as f:
    config = yaml.safe_load(f)

data_sources = config["ontology"]["dataSources"]
sqlite_sources = [ds for ds in data_sources if ds["type"] == "SQLITE"]

if not sqlite_sources:
    raise ValueError("No SQLITE data source found in the configuration.")


# Load SQLite data source by name
def load_sqlite_data_source_by_name(db_name):
    """Load SQLite data source by database name."""
    for source_config in sqlite_sources:
        if source_config["name"] == db_name:
            datasource_name = source_config["name"]
            datasource_path = source_config["database"]
            config = {"database": datasource_path}
            return DataSourceSqlite(datasource_name, config)

    # Fallback to last source if name not found
    last_source_config = sqlite_sources[-1]
    datasource_name = last_source_config["name"]
    datasource_path = last_source_config["database"]
    config = {"database": datasource_path}
    return DataSourceSqlite(datasource_name, config)


def _parse_golden_data(golden):
    """Parse golden parameter to extract SQL query and database ID.

    Args:
        golden: Dictionary with 'result' (SQL query) and 'context' (including db_id) or just the SQL string

    Returns:
        Tuple of (query, db_id) or (None, None) if parsing fails
    """
    try:
        if isinstance(golden, dict):
            query = golden.get("result")
            db_id = golden.get("context", {}).get("db_id")
        else:
            # Fallback to old format (simple string)
            query = golden
            db_id = None

        if not query:
            print("Warning: No SQL query found in golden parameter")
            return None, None

        query = str(query).strip()
        return query, db_id

    except Exception as e:
        print(f"Error parsing golden data: {e}")
        return None, None


def _execute_sql_query(query, db_id):
    """Execute SQL query against the specified database.

    Args:
        query: SQL query string to execute
        db_id: Database identifier, if None uses fallback database

    Returns:
        List of query result data or None if execution fails
    """
    try:
        # Load appropriate data source based on db_id
        if db_id:
            data_source = load_sqlite_data_source_by_name(db_id)
        else:
            # Use the last SQLite data source as fallback
            last_source_config = sqlite_sources[-1]
            datasource_name = last_source_config["name"]
            datasource_path = last_source_config["database"]
            config = {"database": datasource_path}
            data_source = DataSourceSqlite(datasource_name, config)

        data_source.connect()

        # Execute the query
        query_result = data_source.executeQuery(query)
        result_data = query_result.get("data", [])

        # Close the connection
        data_source.close()

        # Convert results to a comparable format
        if not result_data:
            return []
        else:
            return result_data

    except Exception as e:
        print(f"Error executing SQL query: {e}")
        import traceback

        traceback.print_exc()
        return None


def _round_floats_in_data(data, decimal_places=2):
    """Recursively round all float values in a data structure to specified decimal places.

    Args:
        data: Input data structure (can be dict, list, tuple, float, or other types)
        decimal_places: Number of decimal places to round to

    Returns:
        Data structure with all float values rounded
    """
    if isinstance(data, float):
        return round(data, decimal_places)
    elif isinstance(data, dict):
        return {k: _round_floats_in_data(v, decimal_places) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return type(data)(_round_floats_in_data(x, decimal_places) for x in data)
    return data


def _exact_match(gold, predicted):
    """Check if gold and predicted results match exactly.

    Args:
        gold: Expected result
        predicted: Predicted result

    Returns:
        bool: True if results match exactly
    """
    return gold == predicted


def _string_match(gold, predicted):
    """Check if string representations of gold and predicted results match.

    Args:
        gold: Expected result
        predicted: Predicted result

    Returns:
        bool: True if string representations match
    """
    return str(gold) == str(predicted)


def _value_subset_match(gold, predicted):
    """Check if gold values are a subset of predicted values (handles different tuple structures).

    This method handles cases where:
    - gold: [(value1,), (value2,), ...] - single values
    - predicted: [(name1, value1), (name2, value2), ...] - name-value pairs

    Args:
        gold: Expected result (list of tuples with single values)
        predicted: Predicted result (list of tuples with multiple elements)

    Returns:
        bool: True if all gold values are found in predicted results
    """
    if not (isinstance(gold, list) and isinstance(predicted, list)):
        return False

    try:
        # Extract values from gold (assume single-element tuples or direct values)
        gold_values = set()
        for item in gold:
            if isinstance(item, (tuple, list)) and len(item) >= 1:
                gold_values.add(item[0])
            else:
                gold_values.add(item)

        # Extract all values from predicted (check all positions in tuples)
        pred_values = set()
        for item in predicted:
            if isinstance(item, (tuple, list)):
                # Add all numeric values from the tuple
                for val in item:
                    if isinstance(val, (int, float)):
                        pred_values.add(val)
            elif isinstance(item, (int, float)):
                pred_values.add(item)

        # Check if all gold values are in predicted values
        result = gold_values.issubset(pred_values)

        if result:
            print(
                f"Value subset match successful: gold={gold_values}, pred_subset={pred_values}"
            )

        return result

    except Exception as e:
        print(f"Warning: Error in value subset comparison: {e}")
        return False


def _flexible_subset_match(gold, predicted):
    """Check if gold values are contained anywhere in predicted tuples (any column).

    This method handles cases where:
    - gold: [(value1,), (value2,), ...] - single values
    - predicted: [(col1, value1, col3), (col1, value2, col3), ...] - values in any column

    Args:
        gold: Expected result (list of tuples with single values)
        predicted: Predicted result (list of tuples with multiple elements)

    Returns:
        bool: True if all gold values are found in any column of predicted results
    """
    if not (
        isinstance(gold, list)
        and isinstance(predicted, list)
        and len(gold) == len(predicted)
    ):
        return False

    try:
        # Extract values from gold (assume single-element tuples or direct values)
        gold_values = set()
        for item in gold:
            if isinstance(item, (tuple, list)) and len(item) >= 1:
                val = item[0]
                gold_values.add(val)
            else:
                gold_values.add(item)

        # Extract all values from predicted (check all positions in tuples)
        pred_all_values = set()
        for item in predicted:
            if isinstance(item, (tuple, list)):
                # Add all values from the tuple (any data type)
                for val in item:
                    pred_all_values.add(val)
            else:
                pred_all_values.add(item)

        # Check if all gold values are in predicted values (exact match first)
        result = gold_values.issubset(pred_all_values)

        # If exact match fails, try type conversion matching
        if not result:
            # For each gold value, check if it can be found in predicted (with type conversion)
            matched_values = 0
            for gold_val in gold_values:
                found = False
                for pred_val in pred_all_values:
                    # Direct match
                    if gold_val == pred_val:
                        found = True
                        break
                    # Type conversion match
                    try:
                        if (
                            isinstance(gold_val, (int, float))
                            and isinstance(pred_val, str)
                            and float(pred_val) == gold_val
                        ):
                            found = True
                            break
                        if (
                            isinstance(gold_val, str)
                            and isinstance(pred_val, (int, float))
                            and str(pred_val) == gold_val
                        ):
                            found = True
                            break
                        if (
                            isinstance(gold_val, str)
                            and isinstance(pred_val, str)
                            and gold_val.replace(".", "").isdigit()
                            and pred_val.replace(".", "").isdigit()
                            and float(gold_val) == float(pred_val)
                        ):
                            found = True
                            break
                    except (ValueError, TypeError):
                        continue

                if found:
                    matched_values += 1

            result = matched_values == len(gold_values)

        # Add debug information
        # print(f"Debug _flexible_subset_match:")
        # print(f"  gold_values: {gold_values} type: {type(gold_values)} (types: {[type(v) for v in gold_values]})")
        # print(f"  pred_all_values: {pred_all_values} type: {type(pred_all_values)} (types: {[type(v) for v in pred_all_values]})")
        # print(f"  subset check result: {result}")

        # if result:
        #    print(f"Flexible subset match successful!")
        return result

    except Exception as e:
        print(f"Warning: Error in flexible subset comparison: {e}")
        return False


def _compare_results(converted_gold_label, converted_predicted, query, db_id):
    """Compare golden result with predicted answer and output debug information.

    Args:
        converted_gold_label: Expected result from SQL query execution
        converted_predicted: Predicted answer from the model
        query: Original SQL query (for debug output)
        db_id: Database ID (for debug output)

    Returns:
        bool: True if the results match, False otherwise
    """
    try:
        # Round float values in both data structures
        rounded_gold = _round_floats_in_data(converted_gold_label)
        rounded_predicted = _round_floats_in_data(converted_predicted)

        # List of comparison methods to try
        comparison_methods = [
            _exact_match,
            _string_match,
            _value_subset_match,
            _flexible_subset_match,
            # Add new comparison methods here
        ]

        # Try each comparison method until one succeeds
        is_match = any(
            method(rounded_gold, rounded_predicted) for method in comparison_methods
        )

        if not is_match:
            print(f"Comparison failed for db_id '{db_id}':")
            print(
                f"  Query: {query[:100]}..."
                if len(query) > 100
                else f"  Query: {query}"
            )
            result_str = str(converted_gold_label)
            answer_str = str(converted_predicted)
            print(
                f"  Expected: {result_str[:100]}..."
                if len(result_str) > 100
                else f"  Expected: {result_str}"
            )
            print(
                f"  Got: {answer_str[:100]}..."
                if len(answer_str) > 100
                else f"  Got: {answer_str}"
            )

        return is_match

    except Exception as e:
        print(f"Error comparing results: {e}")
        import traceback

        traceback.print_exc()
        return False


def _comparator(converted_gold_label, converted_predicted):
    """Compare golden SQL query result with predicted answer.

    Args:
        converted_gold_label: Dictionary with SQL query result and execution data
        converted_predicted: The predicted answer from the model (should be dict with 'data' field)

    Returns:
        bool: True if the results match, False otherwise
    """
    try:
        # Extract result data from golden
        if (
            not isinstance(converted_gold_label, dict)
            or "result" not in converted_gold_label
        ):
            print("Warning: Invalid golden format")
            return False

        # Handle different types of converted_predicted
        predicted_data = []
        if isinstance(converted_predicted, dict):
            predicted_data = converted_predicted.get("data", [])
        elif isinstance(converted_predicted, (list, tuple)):
            predicted_data = converted_predicted
        else:
            # If it's a string or other type, wrap it in a list
            predicted_data = [converted_predicted] if converted_predicted else []

        # Compare results with predicted answer
        return _compare_results(
            converted_gold_label=converted_gold_label.get("result", []),
            converted_predicted=predicted_data,
            query=converted_gold_label.get("sql", ""),
            db_id=converted_gold_label.get("db_id", ""),
        )

    except Exception as e:
        print(f"Error in comparator: {e}")
        import traceback

        traceback.print_exc()
        return False


def _convert_gold_label(gold_label):
    """Convert gold label to normalized format and execute SQL query.

    Args:
        gold_label: Original gold label (could be dict or string)

    Returns:
        Converted gold label with SQL execution results
    """
    # Step 1: Parse golden data
    query, db_id = _parse_golden_data(gold_label)
    if query is None:
        print("Warning: Failed to parse gold label")
        return None

    # Step 2: Execute SQL query
    result_data = _execute_sql_query(query, db_id)
    if result_data is None:
        print("Warning: Failed to execute SQL query")
        return None

    # Step 3: Create converted result with both SQL and execution results
    converted = {
        "sql": query,
        "db_id": db_id,
        "result": [tuple(item) for item in result_data],
        "_converted": True,
    }

    return converted


def _convert_predicted(predicted):
    """Convert predicted answer to normalized format.

    Args:
        predicted: Raw predicted answer (usually a string)

    Returns:
        dict: Normalized format with 'data' field containing the converted result
    """
    try:
        # Try to parse as Python literal
        return ast.literal_eval(predicted)
    except (ValueError, SyntaxError) as e:
        return predicted


def _convert_query(query):
    return query
