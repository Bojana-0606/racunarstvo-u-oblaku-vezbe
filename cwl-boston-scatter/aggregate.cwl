cwlVersion: v1.2
class: CommandLineTool
requirements:
  DockerRequirement:
    dockerPull: bojana0606/cwl-boston-aggregate:1.0
baseCommand: [python, /app/aggregate.py]
inputs:
  metrics:
    type: File[]
    inputBinding: {position: 1}
outputs:
  summary:
    type: File
    outputBinding: {glob: summary.json}
