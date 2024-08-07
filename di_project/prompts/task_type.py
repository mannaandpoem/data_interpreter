# Prompt for taking on "eda" tasks
EDA_PROMPT = """
The current task is about exploratory data analysis, please note the following:
- Distinguish column types with `select_dtypes` for tailored analysis and visualization, such as correlation.
- Remember to `import numpy as np` before using Numpy functions.
"""

# Prompt for taking on "data_preprocess" tasks
DATA_PREPROCESS_PROMPT = """
The current task is about data preprocessing, please note the following:
- Monitor data types per column, applying appropriate methods.
- Ensure operations are on existing dataset columns.
- Avoid writing processed data to files.
- Avoid any change to label column, such as standardization, etc.
- Prefer alternatives to one-hot encoding for categorical data.
- Only encode or scale necessary columns to allow for potential feature-specific engineering tasks (like time_extract, binning, extraction, etc.) later.
- Each step do data preprocessing to train, must do same for test separately at the same time.
- Always copy the DataFrame before processing it and use the copy to process.
"""

# Prompt for taking on "feature_engineering" tasks
FEATURE_ENGINEERING_PROMPT = """
The current task is about feature engineering. when performing it, please adhere to the following principles:
- Generate as diverse features as possible to improve the model's performance step-by-step.
- Use available feature engineering tools if they are potential impactful.
- Avoid creating redundant or excessively numerous features in one step.
- Exclude ID columns from feature generation and remove them.
- Each feature engineering operation performed on the train set must also applies to the test separately at the same time.
- Avoid using the label column to create features, except for cat encoding.
- Use the data from previous task result if exist, do not mock or reload data yourself.
- Always copy the DataFrame before processing it and use the copy to process.
"""

# Prompt for taking on "model_train" tasks
MODEL_TRAIN_PROMPT = """
The current task is about training a model, please ensure high performance:
- Keep in mind that your user prioritizes results and is highly focused on model performance. So, when needed, feel free to use models of any complexity to improve effectiveness, such as XGBoost, CatBoost, etc.
- If non-numeric columns exist, perform label encode together with all steps.
- Use the data from previous task result directly, do not mock or reload data yourself.
- Set suitable hyperparameters for the model, make metrics as high as possible.
"""

# Prompt for taking on "model_evaluate" tasks
MODEL_EVALUATE_PROMPT = """
The current task is about evaluating a model, please note the following:
- Ensure that the evaluated data is same processed as the training data. If not, remember use object in 'Done Tasks' to transform the data.
- Use trained model from previous task result directly, do not mock or reload model yourself.
"""

# Prompt for taking on "image2webpage" tasks
IMAGE2WEBPAGE_PROMPT = """
The current task is about converting image into webpage code. please note the following:
- Single-Step Code Generation: Execute the entire code generation process in a single step, encompassing HTML, CSS, and JavaScript. Avoid fragmenting the code generation into multiple separate steps to maintain consistency and simplify the development workflow.
- Save webpages: Be sure to use the save method provided.
"""

REPRODUCE_PROMPT = """
The current task is about reproducing the reported issue. Please follow these steps:
- If no reproduction code is provided, skip this step and proceed directly to fixing the bug.
- If reproduction code is provided, follow these steps:
    1. **Add New Test Cases:** Create new test cases in a separate file to reproduce the issue if needed.
    2. **Modify Existing Code:** Adjust the existing code as necessary to replicate the issue.
    3. **Run Targeted Tests:** Execute only the specific test cases related to the issue. Avoid running all test suites directly with `pytest` or similar commands.
"""

LOCATE_PROMPT = """
The current task is about locating the root cause of the issue. Please follow these steps:
- Analyze the code and logs to identify the source of the problem.
- Use debugging tools and techniques to trace the issue to its origin.
"""

FIX_PROMPT = """
The current task is about fixing the identified issue. Please follow these steps:
- Apply the necessary code changes to resolve the issue.
- Ensure that the changes address the root cause and follow coding standards and best practices.
"""

VERIFY_PROMPT = """
The current task is about verifying that the issue has been resolved. Please follow these steps:
- Run the specific test cases related to the issue to confirm the fix.
- After verifying the fix, run the entire test suite to ensure that the modifications have not introduced new issues. This comprehensive testing step is crucial to confirm the stability and reliability of the fix across the application.
"""
