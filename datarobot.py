from dotenv import load_dotenv
import os
import datarobot as dr
from datarobot.models.modeljob import wait_for_async_model_creation
import pandas as pd
from IPython.display import display
#import matplotlib.pyplot as plt
#%matplotlib inline

# wider .head()s
pd.options.display.width = 0
pd.options.display.max_columns = 200
pd.options.display.max_rows = 2000


def load_environment_and_client():
    load_dotenv('.env')

    dr.Client()
    return


def load_datasets():
    # Set to the location of your project.csv and project-test.csv data files
    # Example: dataset_file_path = '/Users/myuser/Downloads/project-test.csv'
    train_dataset_file_path = os.getenv('DR_TRAIN_DATASET_FILEPATH')
    test_dataset_file_path = os.getenv('DR_TEST_DATASET_FILEPATH')

    # Load dataset
    train_dataset = dr.Dataset.create_from_file(train_dataset_file_path)
    test_dataset = dr.Dataset.create_from_file(test_dataset_file_path)
    # ALTERNATIVELY - Load dataset from Pandas DataFrame
    # training_data_df = pd.read_csv(train_dataset_file_path)
    # training_dataset = dr.Dataset.create_from_in_memory_data(training_data_df)
    return train_dataset, test_dataset


def create_project_and_target(training_dataset):
    # Create a new project based on dataset
    project = dr.Project.create_from_dataset(training_dataset.id, project_name=f'Prospect_Sentiment')

    # Set target for dataset training
    project.set_target('signed_contract', worker_count=-1)
    return project


def explore_training_dataset_features(training_dataset, histogram=False):
    # Explore dataset
    all_features = training_dataset.get_all_features()
    for feature in all_features:
        print(feature.name, feature.feature_type, feature.dataset_id)
        print(feature.max, feature.mean, feature.min, feature.std_dev)
        print(feature.na_count, feature.unique_count)
        if histogram:
            feature.get_histogram().plot
    return all_features


def train_model(project):
    # Use training data to build models.
    project.wait_for_autopilot(verbosity=1)
    model = dr.ModelRecommendation.get(project.id).get_model()
    # By default, models are evaluated on the first validation partition. 
    # To start cross-validation, use the Model.cross_validate method:
    model_job_id = model.cross_validate()
    cv_model = wait_for_async_model_creation(project_id=project.id, model_job_id=model_job_id)
    # Check which features were actually used by the model - not all are guaranteed
    feature_names = cv_model.get_features_used()
    print(feature_names)
    return cv_model


def get_top_of_leaderboard(project, verbose = True):
    # Function sourced directly from DataRobot docs: https://app2.datarobot.com/docs/api/guide/modeling-workflow.html
    # A helper method to assemble a dataframe with Leaderboard results and print a summary:
    leaderboard = []
    for m in project.get_models():
        leaderboard.append([m.blueprint_id, m.featurelist.id, m.id, m.model_type, m.sample_pct, m.metrics['AUC']['validation'], m.metrics['AUC']['crossValidation']])
    leaderboard_df = pd.DataFrame(columns = ['bp_id', 'featurelist', 'model_id', 'model', 'pct', 'validation', 'cross_validation'], data = leaderboard)

    if verbose == True:
        # Print a Leaderboard summary:
        print("Unique blueprints tested: " + str(len(leaderboard_df['bp_id'].unique())))
        print("Feature lists tested: " + str(len(leaderboard_df['featurelist'].unique())))
        print("Models trained: " + str(len(leaderboard_df)))
        print("Blueprints in the project repository: " + str(len(project.get_blueprints())))

        # Print the essential information for top models, sorted by accuracy from validation data:
        print("\n\nTop models in the leaderboard:")
        leaderboard_top = leaderboard_df[leaderboard_df['pct'] == 64].sort_values(by = 'cross_validation', ascending = False).head().reset_index(drop = True)
        display(leaderboard_top.drop(columns = ['bp_id', 'featurelist'], inplace = False))

        # Show blueprints of top models:
        # depends on dr_blueprint_workshop library - worth future exploration potentially
        # for index, m in leaderboard_top.iterrows():
        #     Visualize.show_dr_blueprint(dr.Blueprint.get(project.id, m['bp_id']))
    return


def predict_against_model(project, model, test_dataset):
    # Test predictions on new data
    prediction_data = project.upload_dataset(test_dataset)
    predict_job = model.request_predictions(prediction_data.id)
    predictions = predict_job.get_result_when_complete()
    predictions.head()
    return predictions


def main():
    load_environment_and_client()
    train_dataset, test_dataset = load_datasets()
    project = create_project_and_target(train_dataset)
    explore_training_dataset_features(train_dataset, histogram=True)
    model = train_model(project)
    get_top_of_leaderboard(project, verbose=True)
    predictions = predict_against_model(project, model, test_dataset)
    return predictions


# %%
'''
# The below code demonstrates how to deploy the model and make predictions against 
# the deployed model
# Example code sourced from DataRobot documentation: https://app2.datarobot.com/docs/api/reference/predapi/dr-predapi.html
import requests
from pprint import pprint
import json
import os
# JSON records for example autos for which to predict mpg


def deploy_model(model):
    # Deployment steps for Deployment via AI Platform Trial
    deployment = dr.Deployment.create_from_learning_model(model_id=model.id,
                                                          label="MPG Prediction Server",
                                                          description="Deployed with DataRobot client")
    # View deployment stats
    service_stats = deployment.get_service_stats()
    print(service_stats.metrics)
    return deployment


json_data = [
    {
        "cylinders": 4,
        "displacement": 119.0,
        "horsepower": 82.00,
        "weight": 2720.0,
        "acceleration": 19.4,
        "model year": 82,
        "origin": 1,
    },
    {
        "cylinders": 8,
        "displacement": 120.0,
        "horsepower": 79.00,
        "weight": 2625.0,
        "acceleration": 18.6,
        "model year": 82,
        "origin": 1,
    },
]

def get_predictions_from_json(json_data, deployment):
    # Create REST request for prediction API
    prediction_server = deployment.default_prediction_server
    prediction_headers = {
        "Authorization": "Bearer {}".format(os.getenv("DATAROBOT_API_TOKEN")),
        "Content-Type": "application/json",
        "datarobot-key": prediction_server['datarobot-key']
    }

    predictions = requests.post(
        f"{prediction_server.url}/predApi/v1.0/deployments"
        f"/{deployment.id}/predictions",
        headers=prediction_headers,
        data=json.dumps(json_data),
    )
    pprint(predictions.json())
    return
'''