# 03 Recommender Engine - Algorithm Experiments and Evaluation

This directory contains Jupyter notebooks for developing and evaluating recommendation algorithms tasks related to the project.

## Introduction

It consists of several Jupyter Notebooks:

### 01 cc-heuristic.ipynb

This notebook explores the Content-Based Filtering (CC) heuristic approach for recommendation systems. It delves into the fundamental concepts and implementation details of the heuristic-based recommendation approach.

### 02 cc-node similarity.ipynb

This notebook investigates the utilization of node similarity metrics in Content-Based Filtering (CC) recommendation. It explores various node similarity measures and their impact on the effectiveness of the recommendation algorithm.

#### Theory & Improvements: Description Feature Extraction using PhoBERT Embedding

In the traditional content-based filtering approach, the textual description attribute (`description`) of POIs is typically processed using Bag-of-Words (CountVectorizer) or TF-IDF. A major limitation of these methods is that they only count word frequencies and cannot capture semantic meanings, context, or synonyms in the Vietnamese language.

To address this, the recommender engine has been upgraded to integrate **PhoBERT** (`vinai/phobert-base-v2`) - a state-of-the-art pre-trained language model optimized specifically for Vietnamese, based on the RoBERTa architecture.

The text processing pipeline involves:

1. **Vietnamese Word Segmentation**: Utilizing the `PyVi` library (`ViTokenizer.tokenize`) to handle Vietnamese compound words (e.g. converting "thành phố" to "thành_phố"), which aligns with the input format expected by PhoBERT.
2. **Dense Embedding Extraction**: Feeding the segmented text into the pre-trained PhoBERT tokenizer and model. The representation vector of the special `[CLS]` token (index 0) from the model's last hidden state is extracted as the sentence/description embedding (with **768 dimensions**).
3. **Similarity Calculation**: Computing **Cosine Similarity** on these dense vectors instead of token matching, enabling semantic-level similarity comparison between POIs for more intelligent and accurate recommendations.

### 03 cf-userKnn fastRP.ipynb

In this notebook, the Collaborative Filtering (CF) approach with User-Based K-Nearest Neighbors (KNN) and Fast Random Projection (FastRP) techniques is explored. It examines the combination of user-based similarity and dimensionality reduction methods for enhancing recommendation performance.

### 04 cf-itemKnn fastRP.ipynb

Similar to the previous notebook, this one focuses on the Collaborative Filtering (CF) method but employs Item-Based K-Nearest Neighbors (KNN) and Fast Random Projection (FastRP) techniques. It analyzes how item-based similarity and dimensionality reduction can improve the accuracy and efficiency of recommendation systems.

### 05 ensemble - max voting.ipynb

This notebook explores ensemble techniques, specifically the Majority Voting method, for combining the predictions of multiple recommendation models. It investigates how ensemble learning can enhance recommendation performance by aggregating the outputs of individual models.

## Usage

Follow these steps:

1. Ensure the required dependencies are installed.
2. Save the credentials required to connect to the Neo4j database in a file named `neo4j.ini` and place in the root directory of this module.
   Sample `neo4j.ini` File:

```
[NEO4J]
HOST = bolt://[IP]:[PORT]
DATABASE = neo4j
PASSWORD = [PASSWORD]
```

3. Run the desired notebook.

## Dependencies

- `Python 3.x`
- `neo4j`
- `pandas`
- `scikit-learn`
- `matplotlib`
- `py2neo`
- `graphdatascience`
- `torch` (for PyTorch operations)
- `transformers` (to load PhoBERT)
- `pyvi` (for Vietnamese word segmentation)

You can install all dependencies using the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

_(Note: If your system has an NVIDIA GPU, it is highly recommended to install the CUDA-supported version of PyTorch (`torch`) to significantly accelerate the PhoBERT embedding extraction)._

## Contributors

Xiong Ying
Tran Le Anh Tuan

## License

This project is licensed under the [MIT License](LICENSE).
