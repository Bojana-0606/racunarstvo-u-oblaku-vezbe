cwlVersion: v1.2
class: CommandLineTool
requirements:
  DockerRequirement:
    dockerPull: bojana0606/cwl-boston-model:1.0
baseCommand: [python, /app/model.py]
inputs:
  train:
    type: File
    inputBinding: {prefix: --train, position: 1}
  test:
    type: File
    inputBinding: {prefix: --test, position: 2}
  target:
    type: string
    inputBinding: {prefix: --target, position: 3}
outputs:
  metrics:
    type: File
    outputBinding: {glob: metrics.json}
