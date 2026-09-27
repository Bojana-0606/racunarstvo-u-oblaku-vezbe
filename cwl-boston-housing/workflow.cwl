cwlVersion: v1.2
class: Workflow
inputs:
  csv: File
  target: string
  train_percent: int
outputs:
  metrics:
    type: File
    outputSource: train_model/metrics
  preprocessing_report:
    type: File
    outputSource: clean_data/report
steps:
  clean_data:
    run: preprocess.cwl
    in:
      csv: csv
      target: target
      train_percent: train_percent
    out: [train, test, report]
  train_model:
    run: model.cwl
    in:
      train: clean_data/train
      test: clean_data/test
      target: target
    out: [metrics]
