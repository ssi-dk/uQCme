Ensure you read the PLAN.md file for context before making changes.

Ensure you create new tasks in CHANGELOG.md before making changes. Iteratively update CHANGELOG.md as you complete tasks or create new tasks.

We're making a python streamlit app, that is to be maintained by bioinformaticians, this means we want to minimize the use of custom css and js and rely on streamlit's built-in features as much as possible. The app is used to report quality control metrics for microbial sequencing data. The app has inputs:
- `./config.yaml`: A YAML file containing general app configurations and locations of input and output files. This should be modified with app settings.
- from config `input:data`: A TSV file containing the sequencing run data metrics.
- from config `input:mapping`: A YAML file that maps the run data to specific QC metrics for calculation, and defines how the dataframe should be visually shown.
- from config `input:qc_rules`: A TSV file that contains the rules for quality control, the rule file contains tests that are run on the run data.
- from config `input:qc_tests`: A TSV file that checks which contains criteria for passing or failing the QC tests. Samples can fail many tests. It is assumed if you don't fail any tests, you pass all tests.

It will generate outputs:
- from config `output:results`: A TSV file that contains the results of the QC tests, this is also the 

Main functions in the app:
- A file `uQCme.py` of run_data.tsv using all 4 input files. This is a CLI tool that will generate a df/tsv file which acts as the input for the report. It will have two parts, one where it runs each row through the QC rules, saving that to a results df, then another which will examing the QC rules to determine which QC tests are passed or failed, these are 2 new columns in the results df stored as a list.
    - Output: a tsv f
- A streamlit app `app.py` that reads the output of the CLI tool and generates a report, the report uses information from mapping.yaml for how to display the data. It will also use information from QC_tests.tsv for highlighting samples that fail QC tests. If needed the app can load the df from `uQCme.py` directly, but it is recommended to use the output file from `uQCme.py` for performance reasons.
  - We will need the ability to select samples and their id stored to a list, the list can then be passed on with a button. Start with a notification of the affected samples. This will later reference an API.
  - We will need to be able to filter data in multiple ways affecting the filtered data shown in the report. The filtered data is also used as the input for the plots.
  - The sections in mapping.yaml are used to group items in the report. A toggle for each section will be used to show/hide the section. Any columns in the input data which are not defined in mapping.yaml will be placed under the section which contains `unmapped: true` in mapping.yaml. This mapping is expected to be unique.
- A `plot.py` which is used strictly for the streamlit app to generate plots based on the data from the report. All plots are generated based on the df provided by the streamlit app. This will either be the QC_tests.tsv or the output of `uQCme.py`. This should only contain simple code for plotting.


Additional Guiddance:
- The app should be designed to be user-friendly for bioinformaticians, minimizing the need for custom CSS and JavaScript.
- The app should be modular, allowing for easy updates and maintenance
- The app should be driven from the input files where possible, allowing for easy updates to the configuration without changing the code, avoid hardcoding values in the code.
- When performing tests, add them to `./tests`