cwlVersion: v1.2
class: Workflow
requirements:
  ScatterFeatureRequirement: {}
inputs:
  csv: File
  target: string
  k: int
outputs:
  summary:
    type: File
    outputSource: summarize/summary
  fold_metrics:
    type:
      type: array
      items: File
    outputSource: evaluate/metrics
  fold_report:
    type: File
    outputSource: prepare_folds/report
steps:
  prepare_folds:
    run: folds.cwl
    in:
      csv: csv
      target: target
      k: k
    out: [train, test, report]
  evaluate:
    run: model.cwl
    in:
      train: prepare_folds/train
      test: prepare_folds/test
      target: target
    scatter: [train, test]
    scatterMethod: dotproduct
    out: [metrics]
  summarize:
    run: aggregate.cwl
    in:
      metrics: evaluate/metrics
    out: [summary]
