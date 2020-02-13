# label-skill

## Azure Cognitive Search
Custom named entity recognition is a common challenge for most scenarios in Cognitive Search. When building a named entity recognizer, one of the biggest challenges is a lack of labeled data. For organizations that know examples of entities they want to identify, the label skill takes in a list of labels and as an output generates a set of POS tagged sentences with IOB labels for the entities. 

## Setup and Use

1. Configure an Azure Cognitive Search instance to ingest documents from blob storage
2. Setup an enrichment pipeline (skillset) with the label skill
3. Make sure you use the indexer cache option
3. Add a knowledge store projection to project out the labeled data
4. Train a custom entity recognizer based on the labeled dataset
5. Edit the skillset to add the newly trained model as a custom skill
6. Rerun the enrichment pipeline to enrich the data using the new skill


### Deploy the label skill as a ACI Container.

To deploy the label skill as an ACI container follow the following steps:
1. Follow the steps <a href="https://docs.microsoft.com/en-us/azure/container-instances/container-instances-container-group-ssl">documented here</a> to create a SSL endpoint 
2. 
