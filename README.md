# Missing Tree Detector API 

```bash
curl https://aerobotics-api.fly.dev/orchards/216269/missing-trees
```

## Outline

- [1. Requirements](#1-requirements)
  - [Functional Requirements (F)](#functional-requirements-f)
  - [Non-functional Requirements (N)](#non-functional-requirements-n)
- [2. API Design](#2-api-design)
  - [Endpoints](#endpoints)
- [3. Missing Tree Calculation Algorithm](#3-missing-tree-calculation-algorithm)
  - [3.1 Phase 1](#31-phase-1)
  - [3.2 Phase 2](#32-phase-2)
  - [Algorithmic Complexity notes](#algorithmic-complexity-notes)
  - [Assumptions and Shortcomings](#assumptions-and-shortcomings)
- [4. Architecture](#4-architecture)
  - [4.1 Diagram](#41-diagram)
  - [4.2 System Design Considerations](#42-system-design-considerations)
- [5. Project Structure](#5-project-structure)
- [6. Running Locally](#6-running-locally)
- [7. CI/CD](#7-cicd)
  - [7.1 Tests](#71-tests)
  - [7.1 Linting](#72-linting)
- [8. Where I used AI](#8-where-i-used-ai)
- [9. Journal](#9-journal)

## 1. Requirements

### Functional Requirements (F)
1. A client must be able to get a list of the coordinates of missing trees given an Orchard ID. (F1)

### Non-functional Requirements (N)
1. The system should not overload the Aerobotics API with duplicate requests. (N1)
2. The system should determine the missing trees within a reasonable amount of time. (N2)

## 2. API Design
1. The API should ensure that the missing trees endpoint should be paginated.
2. The API should ensure that the page size should be configurable.
3. The API should ensure that it uses offset based pagination to copy approach used by Aerobotics API.
4. The API should always respond in JSON format. 

### Endpoints
| Endpoint        | HTTP Method | Request  | Query Parameters | Response |
| ------------- |:-------------:| -----:| -----: | -----: | 
| /missing_tress      | GET | `orchard_id: string` | `limit: integer, offset integer` | `[]{lng: float64, lat: float64}`

## 3. Missing Tree Calculation Algorithm
To determine if a tree is missing we need to estimate the planting pattern.
At this point in time I don't have access to multiple surveys
of the same area so I can't diff the tree locations. Looking at the aerial image our brain is able to discern if a tree is missing by identifying anomalies in the planting patterns. An anomaly can be identified as an unexpected gap between trees. 

We need to solely rely on the tree locations and their metadata. There are two types of cases we need to handle:
1. Tree(s) within a row are missing.
2. First or last tree(s) within a row are missing.

The strategies for handling each is different so we divide our algorithm into two phases:
1. Find missing tree(s) using inter-row tree spacing as a heuristic.
2. Compare a row's start and end position with the row above and below it.

### 3.1 Phase 1

The first question we need to be able to answer is: how do we know if a group of trees are in a row. To reason about this, assume we have the positions of the trees as cartesian coordinates. A row would be all trees with the same y-coordinate.

![Same-Y](/diagrams/samey.png)

However the trees might not be oriented in this way, so we need to consider something like:

![Same-Y-Angled](/diagrams/sameyangle.png)

Here we see that is a bit more complicated to reason about if a 
tree is in the same row as another. Since we know that if the 
point is perpendicular to the y-axis we can more easily reason about them. Since we only care about the y-axis. Well if we know the angle of the rows, we can rotate our x and y-axis so that this is true again:

![Same-Y-Rotated](/diagrams/sameyrotated.png)

To achieve this we need to reach for some linear algebra. We first need to determine the orientation of the rows (look at code to understand how this is done). We can then find the direction that is perpendicular to that direction and then project the points onto it. This is done by taking the dot product of the tree coordinates and multiplying with the vector $\langle -sin(\theta), cos(\theta) \rangle$ (vector representing direction perpendicular to row orientation) where $\theta$ is the dominant orientation of the rows. 

The dot product tells us how far along the one vector lies on the other. We want to know how far along a tree's position lies along the perpendicular vector. Trees that are next to each other in a row should have the same dot product value, since they should project to the same point on the perpendicular vector.

![Dot-product](/diagrams/dotproduct.png)

We can then group the points that have similar projection values as rows(see above). There are some extra steps needed to achieve this, the projections are not as perfect as above, that are outlined in `notebooks/notebook.ipynb` and in the actual implementation `app/api/orchards/missing_tree_detector/detector_impl.py:40`.

Once we know the rows we can search for missing trees within a row. This is done simply by first calculating the spacing between the tree positions. We use the average spacing as the heuristic to determine if and how many trees are missing between two detected trees in a row.

### 3.2 Phase 2

We now move on to the second phase which needs to detect the missing trees that were not detected in the first phase. Phase 1 does not know if a tree is missing in the first or last positions of a row when only looking at the row. So for the second phase we leverage patterns across rows. For this step we use a sliding-window approach where
we compare three rows at once. The motivation being that **three forms a pattern**. Specifically if something is true before and after the current row, chances are that it should be true for the current row.

![Sliding Window](/diagrams/slidingwindow.png)

Using the above example orchard, we can infer that a tree is missing at the end of the row by comparing the position of the last tree in every row in the window. Additionally if the number of trees (missing trees in row are counted) in the top and
bottom rows are the same, only then do we check the middle row. If the position's of the top and bottom rows are the same and have the same number of trees then the middle one should also be the same. We can confirm this by using an approach similar to Phase 1. Instead of projecting to the vector perpendicular to the row orientation, project onto the row orientation. The idea being that the last tree in the row should project to a similar point on the row direction vector. We then calculate the distance between the middle row's projection and either the top or bottom row's projection value. We then check how many trees can fit into that distance. 

We can also check if trees are missing at the start of the row, this follows a similar approach to above.

### Algorithmic Complexity notes

The most expensive operation in the algorithm is building the KDTree to determine the row's neighbours. This efficiently encodes points according to their spatial information and will scale well for large orchards, but is the most expensive operation in terms of theoretical complexity: $O(n log n)$, where $n$ is the number of detected trees. Calculating the projections and histograms (*with known bins) are $O(n)$, but are generally implemented very efficiently. The autocorrelation calculation is $O(k^2)$ where $k$ is the number of bins, which equates to roughly the number of rows. This could become a bottleneck for very large orchards, but this would require orchards with 10,000s of rows.

However there are some practical slow downs that are not captured by the algorithmic complexity that are discussed in [4.2 System Design Considerations](#42-system-design-considerations). 

### Assumptions and Shortcomings

1. The algorithm assumes that the orchard has a single domninant orientation of trees. For example something like this won't work:

![Two-Directions](/diagrams/twodirections.png)

The last row would be misclassified as three different rows.

2. The algorithm assumes that the trees were planted at the same time and thus also have a similar size. This is critical for estimating the spacing.

3. The second phase won't work if three rows are missing trees in the same positions, since it can't establish a pattern then.

4. When determining rows using row spacing we use a configurable threshold parameter to identify the gaps from the projection.

5. If the orchard is close to a perfect square then this will also not work, since one of the core assumptions of the algorithm is that we can reason discern
spacing across and along rows. 

## 4. Architecture 

### 4.1 Diagram

![Architecture](/diagrams/architecture.png)

The architecture is pretty simple, the key component is the orchards service. This receives the request from the client and orchestrates the steps to gather the latest tree survey for a given orchard. The tree survey is retrieved from the Aerobotics API and the returned tree positions (longitude and latitude coordinates) are then passed to the missing tree detector. The retrieved survey entity is used to query the cache to determine if we have already detected missing trees for it. This will then apply the missing tree detection algorithm to determine if there are any missing trees using the given positions.

### 4.2 System Design Considerations

The missing tree detection algorithm does have a noticeable latency, so to mitigate this we add an in-process cache to mitigate this issue. The amount of memory required to store the list of missing trees for an orchard is generally pretty small so this should be fine for now. If this needs to scale, a Redis instance can be used, this would allow us to have multiple instances of the API that can share this caching layer. 

The missing tree detection algorithm is CPU heavy so handling a lot of requests would require a few vertically scaled machines. Limiting request concurrency and having a shared caching layer will help to mitigate the issue.

The latency for detecting missing trees is acceptable for moderate orchards, if we need to handle larger orchards we need to add a job system. This way the client would instead receive a Job ID when asking if trees are missing in an orchard. The original client request would then be processed in an asynchronous fashion. This is so that the client is not waiting for the response and can continue with other work while waiting for its request to be processed.

## 5. Project Structure

```text
/
├── app/
│   ├── api/
│   │   ├── clients
│   │   │   ├── aerobotics.py - API Client Interface
│   │   │   └── aerobotics_impl.py
│   │   ├── core
│   │   │   └── config.py - App configuration
│   │   └── orchards
│   │       ├── cache.py - Missing trees cache
│   │       ├── model.py - Types
│   │       ├── router.py - Endpoints
│   │       ├── service.py - Logic
│   │       └── missing_tree_detector/
│   │           └── missing_tree_detector_impl.py
│   ├── tests/ Unit-tests
│   └── Dockerfile
├── notebooks/
│   └── notebook.ipynb - Initial Algorithm Draft
├── README.md - Project Description
└── diagrams/ - Extra Diagrams
```

## 6. Running Locally 

This project uses `uv` as the package manager. Install [here](https://docs.astral.sh/uv/getting-started/installation/).

```bash
cd app/
uv sync
uv run uvicorn api.main:app --reload
```

## 7. CI/CD

The API is as Fly.io machine on [fly.io](https://fly.io/). A fly.io machine is an AWS firecracker microVM. Fly.IO was chosen since it has a secret manager, supports scaling down instances that are not used, easy scaling if needed, SSL certificate management and can deploy using a single command.

A github workflow was also setup so that pushes to the main branch automatically deploy a new version of the API. A deployment is only made if the tests and linting checks pass. We also only execute the pipeline when files inside the app directory are changed.

### 7.1 Tests

```bash 
cd app/
uv run pytest
```
### 7.2 Linting

```bash
cd app/
uv run ruff check
```

## 8. Where I used AI

I declare that I used an AI coding to aid in certain aspects of this project. 

1. I used AI to help me get an approach to group the different projections into rows in a resilient way.
2. I used a coding agent to generate the FastAPI boilerplate code.
3. I used AI to assist with what functions to use in NumPy.
4. I used AI to generate the visualisations in the notebooks/notebook.ipynb.
5. I used AI to generate the fly.toml file.
6. I used AI to help me generate the methods to generate synthetic data to test algorithm.
7. I used AI to research a suitable linting and testing setup.
8. I used AI to help with understanding some of the linear algebra and trigonometry calculations.

## 9. Journal

**Session 1**
- Spent time trying to understand the problem.
- Wrote down an initial draft of functional and non-functional requirements.
- Spent time exploring API to understand what information needs to be gathered to determine which trees are missing.
    - Looked at API response shapes
    - Walked through an example manually, by choosing a random orchard and walking through the steps to determine the 
        missing trees (retrieve orchard, get survey from orchard id and then call missing trees endpoint).
- Created Git project and rough project outline with folders.
- Added README.md with rough outline.
- Started brainstorming high-level algorithm.

**Session 2**
- Created notebook to aid in visualising algorithm steps.
- Got algorithm working to identify trees in notebook.
- Wrote out algorithm outline and motivation.

**Session 3**
- Rewrote algorithm from notebook for API implementation.
- Added code for setting up HTTP server and added missing trees route.
- Added unit tests for the tree detection algorithm
- Added Dockerfile and additional configuration to deploy API 
- Deployed API
- Added Github Workflow to deploy app when pushing to main

**Session 4**
- Reviewed Algorithm and thought of assumptions and edge cases