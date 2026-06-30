# Kyle Smith - Aerobotics Assessment

## Outline

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
| /missing_tress      | GET | `orchard_id: string` | `limit: integer, offset integer` | `[]{long: float64, lat: float64}`

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

To achieve this we need to reach for some linear algebra. We first need to determine the orientation of the rows (look at code to understand how this is done). We can then find the direction that is perpendicular to that direction and then project the points onto it. This is done by taking the dot product of the tree coordinates and multiplying with the vector $\langle -sin(\theta), cos(\theta) \rangle$ where $\theta$ is the dominant orientation of the rows. The dot product tells us how far along the one vector lies on the other. We want to know how far along a tree's position lies along the perpendicular vector. Trees that 
have are next to each other in a row should have the same dot product value, since they should project to the same point on the perpendicular vector.

We can then group the points that have similar projection(dot product result) values as rows. There are some extra steps needed to achieve this, that are outlined in notebooks/notebook.ipynb.

With the rows we can determine determine the mean distance between trees in that row.
With the mean we are able to identify gaps within the row, by walking across the row and calculating the difference between the trees in a pairwise fashion. We detect the number trees that are missing by dividing the distance by the average tree spacing distance. To determine the positions of the missing trees we need a method to estimate this. Linear interpolation makes sense here, since it is a simple method that can be used to evenly space elements in a line. The trees are assumed to be evenly spaced and in a line.

### 3.2 Phase 2

We now move on to the second phase which needs to detect the missing trees that were not detected in the first phase. Phase 1 does not know if a tree is missing in the first or last positions of a row when only looking at the row. So for the second phase we leverage patterns across rows. For this step we use a sliding-window approach where
we compare three rows at once. The motivation being that **three forms a pattern**. Specifically if something is true before and after the current row, chances are that it should be true for the current row.

![Sliding Window](/diagrams/slidingwindow.png)

Using the above example orchard, we can infer that a tree is missing at the end of the row by comparing the position of the last tree in every row in the window. Additionally if the number of trees (missing trees in row are counted) in the top and
bottom rows are the same, only then do we check the middle row. If the position's of the top and bottom rows are the same and have the same number of trees then the middle one should also be the same. We can confirm this by using an approach similar to Phase 1. Instead of projecting to the vector perpendicular to the row orientation, project onto the row orientation. The idea being that the last tree in the row should project to a similar point on the row direction vector. We then calculate the distance between the middle row's projection and either the top or bottom row's projection value. We then check how many trees can fit into that distance. 

We can also check if trees are missing at the start of the row, this follows a similar approach to above.

### Algorithmic Complexity notes

The most expensive operation in the algorithm is building the KDTree to determine the row's neighbours. This efficiently encodes points according to their spatial information and will scale well for large orchards, but is the most expensive operation in terms of theoretical complexity: $O(n log n)$. Calculating the projections and histograms (*with known bins) are $O(n)$. The autocorrelation calculation is $O(k^2)$ where $k$ is the number of bins, which equates to roughly the number of rows. This could become a bottleneck for very large orchards, but this would require orchards with 10,000s of rows.

### Assumptions and Shortcomings

1. The algorithm assumes that the orchard has a single domninant orientation of trees. For example something like this won't work:

![Two-Directions](/diagrams/twodirections.png)

The last row would be misclassified as three different rows.

2. The algorithm assumes that the trees were planted at the same time and thus also have a similar size. This is critical for estimating the spacing.

3. The second phase won't work if three rows are missing trees in the same positions, since it can't establish a pattern then.

## 4. Architecture

## 5. Project Structure

## 6. Running tests

## 7. Journal

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
