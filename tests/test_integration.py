"""Chemprop integration tests."""
from flask import url_for
from io import BytesIO
import json
import os
from tempfile import TemporaryDirectory
from typing import List
import unittest
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd
from parameterized import parameterized

from chemprop.constants import TEST_SCORES_FILE_NAME
from chemprop.hyperparameter_optimization import chemprop_hyperopt
from chemprop.interpret import chemprop_interpret
from chemprop.sklearn_predict import sklearn_predict
from chemprop.sklearn_train import sklearn_train
from chemprop.train import chemprop_train, chemprop_predict, evaluate_predictions
from chemprop.web.wsgi import build_app
from chemprop.spectra_utils import normalize_spectra, load_phase_mask
from chemprop.features import load_features


TEST_DATA_DIR = 'tests/data'
SEED = 0
EPOCHS = 10
NUM_FOLDS = 3
NUM_ITER = 2
DELTA = 0.05


class ChempropTests(TestCase):
    @staticmethod
    def create_raw_train_args(dataset_type: str,
                              metric: str,
                              save_dir: str,
                              model_type: str = 'chemprop',
                              flags: List[str] = None) -> List[str]:
        """Creates a list of raw command line arguments for training."""
        return [
            'train',  # Note: not actually used, just a placeholder
            '--data_path', os.path.join(TEST_DATA_DIR, f'{dataset_type}.csv'), # Note: adding another --data_path argument will overwrite this one
            '--dataset_type', dataset_type,
            '--epochs', str(EPOCHS),
            '--num_folds', str(NUM_FOLDS),
            '--seed', str(SEED),
            '--metric', metric,
            '--save_dir', save_dir,
            '--quiet',
            '--empty_cache'
        ] + (['--model_type', model_type] if model_type != 'chemprop' else []) + (flags if flags is not None else [])

    @staticmethod
    def create_raw_predict_args(dataset_type: str,
                                preds_path: str,
                                checkpoint_dir: str,
                                flags: List[str] = None) -> List[str]:
        """Creates a list of raw command line arguments for predicting."""
        return [
            'predict',  # Note: not actually used, just a placeholder
            '--test_path', os.path.join(TEST_DATA_DIR, f'{dataset_type}_test_smiles.csv'),
            '--preds_path', preds_path,
            '--checkpoint_dir', checkpoint_dir
        ] + (flags if flags is not None else [])

    @staticmethod
    def create_raw_hyperopt_args(dataset_type: str,
                                 config_save_path: str,
                                 save_dir: str,
                                 flags: List[str] = None) -> List[str]:
        """Creates a list of raw command line arguments for hyperparameter optimization."""
        return [
            'hyperopt',  # Note: not actually used, just a placeholder
            '--data_path', os.path.join(TEST_DATA_DIR, f'{dataset_type}.csv'),
            '--dataset_type', dataset_type,
            '--epochs', str(EPOCHS),
            '--num_iter', str(NUM_ITER),
            '--config_save_path', config_save_path,
            '--save_dir', save_dir,
            '--quiet',
            '--empty_cache'
        ] + (flags if flags is not None else [])

    @staticmethod
    def create_raw_interpret_args(dataset_type: str,
                                  checkpoint_dir: str,
                                  flags: List[str] = None) -> List[str]:
        """Creates a list of raw command line arguments for interpretation."""
        return [
            'interpret',  # Note: not actually used, just a placeholder
            '--data_path', os.path.join(TEST_DATA_DIR, f'{dataset_type}_test_smiles.csv'),
            '--checkpoint_dir', checkpoint_dir
        ] + (flags if flags is not None else [])

    def train(self,
              dataset_type: str,
              metric: str,
              save_dir: str,
              model_type: str = 'chemprop',
              flags: List[str] = None):
        # Set up command line arguments
        raw_args = self.create_raw_train_args(
            dataset_type=dataset_type,
            metric=metric,
            save_dir=save_dir,
            model_type=model_type,
            flags=flags
        )

        # Train
        with patch('sys.argv', raw_args):
            command_line = ' '.join(raw_args[1:])

            if model_type == 'chemprop':
                print(f'python train.py {command_line}')
                chemprop_train()
            else:
                print(f'python sklearn_train.py {command_line}')
                sklearn_train()

    def predict(self,
                dataset_type: str,
                preds_path: str,
                save_dir: str,
                model_type: str = 'chemprop',
                flags: List[str] = None):
        # Set up command line arguments
        raw_args = self.create_raw_predict_args(
            dataset_type=dataset_type,
            preds_path=preds_path,
            checkpoint_dir=save_dir,
            flags=flags
        )

        # Predict
        with patch('sys.argv', raw_args):
            command_line = ' '.join(raw_args[1:])

            if model_type == 'chemprop':
                print(f'python predict.py {command_line}')
                chemprop_predict()
            else:
                print(f'python sklearn_predict.py {command_line}')
                sklearn_predict()

    def hyperopt(self,
                 dataset_type: str,
                 config_save_path: str,
                 save_dir: str,
                 flags: List[str] = None):
        # Set up command line arguments
        raw_args = self.create_raw_hyperopt_args(
            dataset_type=dataset_type,
            config_save_path=config_save_path,
            save_dir=save_dir,
            flags=flags
        )

        # Hyperopt
        with patch('sys.argv', raw_args):
            command_line = ' '.join(raw_args[1:])
            print(f'python hyperparameter_optimization.py {command_line}')
            chemprop_hyperopt()

    def interpret(self,
                  dataset_type: str,
                  checkpoint_dir: str,
                  flags: List[str] = None):
        # Set up command line arguments
        raw_args = self.create_raw_interpret_args(
            dataset_type=dataset_type,
            checkpoint_dir=checkpoint_dir,
            flags=flags
        )

        # Interpret
        with patch('sys.argv', raw_args):
            command_line = ' '.join(raw_args[1:])
            print(f'python interpret.py {command_line}')
            chemprop_interpret()

    @parameterized.expand([
        (
                'sklearn_random_forest',
                'random_forest',
                'rmse',
                1.582733
        ),
        (
                'sklearn_svm',
                'svm',
                'rmse',
                1.698927
        ),
        (
                'chemprop',
                'chemprop',
                'rmse',
                1.237620
        ),
        (
                'chemprop_scaffold_split',
                'chemprop',
                'rmse',
                1.433300,
                ['--split_type', 'scaffold_balanced']
        ),
        (
                'chemprop_morgan_features_generator',
                'chemprop',
                'rmse',
                1.834947,
                ['--features_generator', 'morgan']
        ),
        (
                'chemprop_rdkit_features_path',
                'chemprop',
                'rmse',
                0.807828,
                ['--features_path', os.path.join(TEST_DATA_DIR, 'regression.npz'), '--no_features_scaling']
        ),
        (
                'chemprop_bounded_mse_loss',
                'chemprop',
                'bounded_mse',
                1.4771486,
                [
                    '--loss_function', 'bounded_mse',
                    '--data_path', os.path.join(TEST_DATA_DIR, 'regression_inequality.csv')
                ]
        )
    ])
    def test_train_single_task_regression(self,
                                          name: str,
                                          model_type: str,
                                          metric: str,
                                          expected_score: float,
                                          train_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            self.train(
                dataset_type='regression',
                metric=metric,
                save_dir=save_dir,
                model_type=model_type,
                flags=train_flags
            )

            # Check results
            test_scores_data = pd.read_csv(os.path.join(save_dir, TEST_SCORES_FILE_NAME))
            test_scores = test_scores_data[f'Mean {metric}']
            self.assertEqual(len(test_scores), 1)

            mean_score = test_scores.mean()
            self.assertAlmostEqual(mean_score, expected_score, delta=DELTA*expected_score)

    @parameterized.expand([
        (
                'chemprop',
                'chemprop',
                'auc',
                0.691205
        ),
        (
                'chemprop_morgan_features_generator',
                'chemprop',
                'auc',
                0.619021,
                ['--features_generator', 'morgan']
        ),
        (
                'chemprop_rdkit_features_path',
                'chemprop',
                'auc',
                0.659145,
                ['--features_path', os.path.join(TEST_DATA_DIR, 'classification.npz'), '--no_features_scaling']
        ),
        (
                'chemprop_mcc_metric',
                'chemprop',
                'mcc',
                0.17130675,
                ['--metric', 'mcc', '--data_path', os.path.join(TEST_DATA_DIR, 'classification_common.csv'), '--class_balance']
        ),
        (
                'chemprop_f1_metric',
                'chemprop',
                'f1',
                0.221176,
                ['--metric', 'f1', '--data_path', os.path.join(TEST_DATA_DIR, 'classification_common.csv'), '--class_balance']
        ),
        (
                'chemprop_mcc_loss',
                'chemprop',
                'auc',
                0.6941197,
                ['--loss_function', 'mcc', '--data_path', os.path.join(TEST_DATA_DIR, 'classification_common.csv'), '--class_balance']
        )
    ])
    def test_train_multi_task_classification(self,
                                             name: str,
                                             model_type: str,
                                             metric: str,
                                             expected_score: float,
                                             train_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            self.train(
                dataset_type='classification',
                metric=metric,
                save_dir=save_dir,
                model_type=model_type,
                flags=train_flags
            )

            # Check results
            test_scores_data = pd.read_csv(os.path.join(save_dir, TEST_SCORES_FILE_NAME))
            test_scores = test_scores_data[f'Mean {metric}']

            mean_score = test_scores.mean()
            self.assertAlmostEqual(mean_score, expected_score, delta=DELTA*expected_score)

    @parameterized.expand([
        (
                'sklearn_random_forest',
                'random_forest',
                0.945589
        ),
        (
                'sklearn_svm',
                'svm',
                1.015136
        ),
        (
                'chemprop',
                'chemprop',
                0.561477
        ),
        (
                'chemprop_morgan_features_generator',
                'chemprop',
                3.825271,
                ['--features_generator', 'morgan'],
                ['--features_generator', 'morgan']
        ),
        (
                'chemprop_rdkit_features_path',
                'chemprop',
                0.693359,
                ['--features_path', os.path.join(TEST_DATA_DIR, 'regression.npz'), '--no_features_scaling'],
                ['--features_path', os.path.join(TEST_DATA_DIR, 'regression_test.npz'), '--no_features_scaling']
        )
    ])
    def test_predict_single_task_regression(self,
                                            name: str,
                                            model_type: str,
                                            expected_score: float,
                                            train_flags: List[str] = None,
                                            predict_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            dataset_type = 'regression'
            self.train(
                dataset_type=dataset_type,
                metric='rmse',
                save_dir=save_dir,
                model_type=model_type,
                flags=train_flags
            )

            # Predict
            preds_path = os.path.join(save_dir, 'preds.csv')
            self.predict(
                dataset_type=dataset_type,
                preds_path=preds_path,
                save_dir=save_dir,
                model_type=model_type,
                flags=predict_flags
            )

            # Check results
            pred = pd.read_csv(preds_path)
            true = pd.read_csv(os.path.join(TEST_DATA_DIR, f'{dataset_type}_test_true.csv'))
            self.assertEqual(list(pred.keys()), list(true.keys()))
            self.assertEqual(list(pred['smiles']), list(true['smiles']))

            pred, true = pred.drop(columns=['smiles']), true.drop(columns=['smiles'])
            pred, true = pred.to_numpy(), true.to_numpy()
            mse = float(np.nanmean((pred - true) ** 2))
            self.assertAlmostEqual(mse, expected_score, delta=DELTA*expected_score)

    @parameterized.expand([
        (
                'chemprop',
                'chemprop',
                0.064605
        ),
        (
                'chemprop_morgan_features_generator',
                'chemprop',
                0.083170,
                ['--features_generator', 'morgan'],
                ['--features_generator', 'morgan']
        ),
        (
                'chemprop_rdkit_features_path',
                'chemprop',
                0.064972,
                ['--features_path', os.path.join(TEST_DATA_DIR, 'classification.npz'), '--no_features_scaling'],
                ['--features_path', os.path.join(TEST_DATA_DIR, 'classification_test.npz'), '--no_features_scaling']
        )
    ])
    def test_predict_multi_task_classification(self,
                                               name: str,
                                               model_type: str,
                                               expected_score: float,
                                               train_flags: List[str] = None,
                                               predict_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            dataset_type = 'classification'
            self.train(
                dataset_type=dataset_type,
                metric='auc',
                save_dir=save_dir,
                model_type=model_type,
                flags=train_flags
            )

            # Predict
            preds_path = os.path.join(save_dir, 'preds.csv')
            self.predict(
                dataset_type=dataset_type,
                preds_path=preds_path,
                save_dir=save_dir,
                model_type=model_type,
                flags=predict_flags
            )

            # Check results
            pred = pd.read_csv(preds_path)
            true = pd.read_csv(os.path.join(TEST_DATA_DIR, f'{dataset_type}_test_true.csv'))
            self.assertEqual(list(pred.keys()), list(true.keys()))
            self.assertEqual(list(pred['smiles']), list(true['smiles']))

            pred, true = pred.drop(columns=['smiles']), true.drop(columns=['smiles'])
            pred, true = pred.to_numpy(), true.to_numpy()
            mse = float(np.nanmean((pred - true) ** 2))
            self.assertAlmostEqual(mse, expected_score, delta=DELTA*expected_score)

    def test_chemprop_hyperopt(self):
        with TemporaryDirectory() as save_dir:
            # Train
            config_save_path = os.path.join(save_dir, 'config.json')
            self.hyperopt(
                dataset_type='regression',
                config_save_path=config_save_path,
                save_dir=save_dir
            )

            # Check results
            with open(config_save_path) as f:
                config = json.load(f)

            parameters = {'depth': (2, 6), 'hidden_size': (300, 2400), 'ffn_num_layers': (1, 3), 'dropout': (0.0, 0.4)}

            self.assertEqual(set(config.keys()), set(parameters.keys()))

            for parameter, (min_value, max_value) in parameters.items():
                self.assertTrue(min_value <= config[parameter] <= max_value)

    @parameterized.expand([
        (
                'chemprop',
        ),
        (
                'chemprop_morgan_features_generator',
                ['--features_generator', 'morgan'],
                ['--features_generator', 'morgan']
        ),
    ])
    def test_interpret_single_task_regression(self,
                                              name: str,
                                              train_flags: List[str] = None,
                                              interpret_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            dataset_type = 'regression'
            self.train(
                dataset_type=dataset_type,
                metric='rmse',
                save_dir=save_dir,
                flags=train_flags
            )

            # Interpret
            try:
                self.interpret(
                    dataset_type=dataset_type,
                    checkpoint_dir=save_dir,
                    flags=interpret_flags
                )
            except Exception as e:
                self.fail(f'Interpretation failed with error: {e}')

    def test_chemprop_web(self):
        with TemporaryDirectory() as root_dir:
            app = build_app(root_folder=root_dir, init_db=True)

            app.config['TESTING'] = True

            data_path = 'regression.csv'
            test_path = 'regression_test_smiles.csv'
            dataset_name = 'regression_data'
            dataset_type = 'regression'
            checkpoint_name = 'regression_ckpt'
            ckpt_name = data_name = '1'
            epochs = 3
            ensemble_size = 1

            with open(os.path.join(TEST_DATA_DIR, data_path)) as f:
                train_data = BytesIO(f.read().encode('utf-8'))

            with open(os.path.join(TEST_DATA_DIR, test_path)) as f:
                test_smiles = f.read()

            with app.test_client() as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)

                # Upload data
                response = client.post(
                    url_for('upload_data', return_page='home'),
                    data={
                        'dataset': (train_data, data_path),
                        'datasetName': dataset_name
                    }
                )
                self.assertEqual(response.status_code, 302)

                # Train
                response = client.post(
                    url_for('train'),
                    data={
                        'dataName': data_name,
                        'epochs': epochs,
                        'ensembleSize': ensemble_size,
                        'checkpointName': checkpoint_name,
                        'datasetType': dataset_type,
                        'useProgressBar': False
                    }
                )
                self.assertEqual(response.status_code, 200)

                # Predict
                response = client.post(
                    url_for('predict'),
                    data={
                        'checkpointName': ckpt_name,
                        'textSmiles': test_smiles
                    }
                )
                self.assertEqual(response.status_code, 200)

    @parameterized.expand([
        (
            'spectra',
            'chemprop',
            0.001737553471704,
            [
                '--data_path', os.path.join(TEST_DATA_DIR, 'spectra.csv'),
                '--features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
                '--split_type', 'random_with_repeated_smiles'
            ]
        ),
        (
            'spectra_excluded_targets',
            'chemprop',
            0.001617717412785,
            [
                '--data_path', os.path.join(TEST_DATA_DIR, 'spectra_exclusions.csv'),
                '--features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
                '--split_type', 'random_with_repeated_smiles'
            ]
        ),
        (
            'spectra_phase_features',
            'chemprop',
            0.001421314775383,
            [
                '--data_path', os.path.join(TEST_DATA_DIR, 'spectra_exclusions.csv'),
                '--phase_features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
                '--spectra_phase_mask_path', os.path.join(TEST_DATA_DIR, 'spectra_mask.csv'),
                '--split_type', 'random_with_repeated_smiles'
            ]
        ),
    ])
    def test_train_spectra(self,
                                          name: str,
                                          model_type: str,
                                          expected_score: float,
                                          train_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            metric = 'sid'
            self.train(
                dataset_type = 'spectra',
                metric = metric,
                save_dir = save_dir,
                model_type = model_type,
                flags = train_flags
            )

            # Check results
            test_scores_data = pd.read_csv(os.path.join(save_dir, TEST_SCORES_FILE_NAME))
            test_scores = test_scores_data[f'Mean {metric}']
            self.assertEqual(len(test_scores), 1)

            mean_score = test_scores.mean()
            self.assertAlmostEqual(mean_score, expected_score, delta=DELTA*expected_score)

    @parameterized.expand([
        (
            'spectra',
            'chemprop',
            0.0014090729236303759,
            0,
            [
                '--data_path', os.path.join(TEST_DATA_DIR, 'spectra.csv'),
                '--features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
                '--split_type', 'random_with_repeated_smiles'
            ],
            [
                '--features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
            ]
        ),
        (
            'spectra_phase_features',
            'chemprop',
            0.0009571740389124222,
            284,
            [
                '--data_path', os.path.join(TEST_DATA_DIR, 'spectra_exclusions.csv'),
                '--phase_features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
                '--spectra_phase_mask_path', os.path.join(TEST_DATA_DIR, 'spectra_mask.csv'),
                '--split_type', 'random_with_repeated_smiles'
            ],
            [
                '--phase_features_path', os.path.join(TEST_DATA_DIR, 'spectra_features.csv'),
            ]
        ),
    ])
    def test_predict_spectra(self,
                                            name: str,
                                            model_type: str,
                                            expected_score: float,
                                            expected_nans: int,
                                            train_flags: List[str] = None,
                                            predict_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            dataset_type = 'spectra'
            self.train(
                dataset_type=dataset_type,
                metric='sid',
                save_dir=save_dir,
                model_type=model_type,
                flags=train_flags
            )

            # Predict
            preds_path = os.path.join(save_dir, 'preds.csv')
            self.predict(
                dataset_type=dataset_type,
                preds_path=preds_path,
                save_dir=save_dir,
                model_type=model_type,
                flags=predict_flags
            )

            # Check results
            pred = pd.read_csv(preds_path)
            true = pd.read_csv(os.path.join(TEST_DATA_DIR, 'spectra.csv'))
            self.assertEqual(list(pred.keys()), list(true.keys()))
            self.assertEqual(list(pred['smiles']), list(true['smiles']))

            pred, true = pred.drop(columns=['smiles']), true.drop(columns=['smiles'])
            pred, true = pred.to_numpy(), true.to_numpy()
            phase_features = load_features(predict_flags[1])
            if '--spectra_phase_mask_path' in train_flags:
                mask = load_phase_mask(train_flags[5])
            else:
                mask = None
            true = normalize_spectra(true,phase_features,mask)
            sid = evaluate_predictions(preds=pred, targets=true, num_tasks=len(true[0]), metrics=['sid'], dataset_type='spectra')['sid'][0]
            self.assertAlmostEqual(sid, expected_score, delta=DELTA*expected_score)
            self.assertEqual(np.sum(np.isnan(pred)),expected_nans)

    @parameterized.expand([
        (
                'chemprop_reaction',
                'chemprop',
                2.019870,
                ['--reaction', '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_regression.csv')]
        ),
        (
                'chemprop_scaffold_split',
                'chemprop',
                1.907502,
                ['--reaction', '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_regression.csv'),'--split_type', 'scaffold_balanced']
        ),
        (
                'chemprop_morgan_features_generator',
                'chemprop',
                2.846405,
                ['--reaction', '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_regression.csv'),'--features_generator', 'morgan']
        ),
        (
                'chemprop_reaction_explicit_h',
                'chemprop',
                2.139865,
                ['--reaction', '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_regression.csv'), '--explicit_h']
         )
    ])
    def test_train_single_task_regression_reaction(self,
                                          name: str,
                                          model_type: str,
                                          expected_score: float,
                                          train_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            metric = 'rmse'
            self.train(
                dataset_type = 'regression',
                metric = metric,
                save_dir = save_dir,
                model_type = model_type,
                flags = train_flags
            )

            # Check results
            test_scores_data = pd.read_csv(os.path.join(save_dir, TEST_SCORES_FILE_NAME))
            test_scores = test_scores_data[f'Mean {metric}']
            self.assertEqual(len(test_scores), 1)

            mean_score = test_scores.mean()
            self.assertAlmostEqual(mean_score, expected_score, delta=DELTA*expected_score)

    @parameterized.expand([
        (
                'chemprop_reaction_solvent',
                'chemprop',
                2.912189,
                ['--reaction_solvent', '--number_of_molecules', '2',
                 '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_solvent_regression.csv')]
        ),
        (
                'chemprop_morgan_features_generator',
                'chemprop',
                3.465252,
                ['--reaction_solvent', '--number_of_molecules', '2',
                 '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_solvent_regression.csv'),'--features_generator', 'morgan']
        ),
        (
                'chemprop_reaction_solvent_explicit_h',
                'chemprop',
                2.805125,
                ['--reaction_solvent', '--number_of_molecules', '2',
                 '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_solvent_regression.csv'), '--explicit_h']
         ),
        (
                'chemprop_reaction_solvent_explicit_h_adding_h',
                'chemprop',
                2.826695,
                ['--reaction_solvent', '--number_of_molecules', '2',
                 '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_solvent_regression.csv'), '--explicit_h', '--adding_h']
        ),
        (
                'chemprop_reaction_solvent_diff_mpn_size',
                'chemprop',
                2.791803,
                ['--reaction_solvent', '--number_of_molecules', '2',
                 '--data_path', os.path.join(TEST_DATA_DIR, 'reaction_solvent_regression.csv'), '--hidden_size', '500',
                 '--hidden_size_solvent', '250']
        )
    ])
    def test_train_single_task_regression_reaction_solvent(self,
                                          name: str,
                                          model_type: str,
                                          expected_score: float,
                                          train_flags: List[str] = None):
        with TemporaryDirectory() as save_dir:
            # Train
            metric = 'rmse'
            self.train(
                dataset_type = 'regression',
                metric = metric,
                save_dir = save_dir,
                model_type = model_type,
                flags = train_flags
            )

            # Check results
            test_scores_data = pd.read_csv(os.path.join(save_dir, TEST_SCORES_FILE_NAME))
            test_scores = test_scores_data[f'Mean {metric}']
            self.assertEqual(len(test_scores), 1)

            mean_score = test_scores.mean()
            self.assertAlmostEqual(mean_score, expected_score, delta=DELTA*expected_score)

if __name__ == '__main__':
    unittest.main()
