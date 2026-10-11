import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', required=True)
    parser.add_argument('--test', required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    if args.target not in train or args.target not in test:
        parser.error('Ciljna kolona nedostaje u trening ili test CSV fajlu')
    columns = [col for col in train.columns if col != args.target]
    if not columns or list(test.columns) != list(train.columns):
        parser.error('Trening i test moraju imati iste kolone istim redosledom')
    if train.isna().any().any() or test.isna().any().any():
        parser.error('Podaci posle predobrade ne smeju imati nedostajuće vrednosti')

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1)
    model.fit(train[columns], train[args.target])
    truth = test[args.target].to_numpy(dtype=float)
    predicted = model.predict(test[columns])
    rmse = float(np.sqrt(mean_squared_error(truth, predicted)))
    denominator = float(np.mean(np.abs(truth)))
    metrics = {
        'target': args.target,
        'model': 'RandomForestRegressor(n_estimators=100, random_state=42)',
        'train_rows': len(train),
        'test_rows': len(test),
        'RMSE': rmse,
        'PRMSE_percent': 100 * rmse / denominator if denominator != 0 else None,
        'PRMSE_definition': '100 * RMSE / mean(abs(y_test))',
        'MAE': float(mean_absolute_error(truth, predicted)),
        'R2': float(r2_score(truth, predicted)),
    }
    Path('metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
