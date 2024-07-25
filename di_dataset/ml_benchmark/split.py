# This file is used to split the raw datasets into train and eval datasets and all files have been processed.
import os
import pandas as pd
from sklearn.model_selection import train_test_split

TRAIN_VAL_SPLIT = 0.8  # 80% of the data is used for training, 20% for evaluation
SEED = 100  # Random seed for consistent splitting

# List of datasets to split
datasets = [
    "./04_titanic/raw/train.csv",
    "./05_house-prices-advanced-regression-techniques/raw/train.csv",
    "./06_santander-customer-transaction-prediction/raw/train.csv",
    "./07_icr-identify-age-related-conditions/raw/train.csv",
    "./08_santander-value-prediction-challenge/raw/train.csv",
]

# Split the dataset into 80% for training and 20% for testing with a random seed of 100 to ensure consistent splitting
for dataset in datasets:
    if not os.path.exists(dataset):
        continue
    df = pd.read_csv(dataset)
    train, test = train_test_split(df, test_size=1 - TRAIN_VAL_SPLIT, random_state=SEED)

    # save the train and eval splits as csv files
    train.to_csv(dataset.replace("raw/train.csv", "split_train.csv"), index=False)
    test.to_csv(dataset.replace("raw/train.csv", "split_eval.csv"), index=False)
    print(f"Successfully split {dataset} into train and eval datasets")
