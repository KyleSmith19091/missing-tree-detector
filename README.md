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

## Missing Tree Calculation Algorithm (OrchardID == 216269, 25319)
To determine if a tree is missing we need to estimate the planting pattern. We know the location of a tree within an orchard
using the tree survey of the orchard. However we need to determine how they are organised, since we can not assume the trees are arranged in a perfect grid. 

### Naive Approach

To determine where trees are possibly missing we need to first group the trees from the survey into rows. We can then check for gaps by comparing the distances between the trees in the row. The edge case here is determining if there is a tree missing in the first or last indices of the row. We can not rely on the average distance between the first and last tree in a row between the bounding polygon for the orchard. This is because the polygon might be complex and the vector between the tree and polygon boundary might not be orthogonal. For example:

![Orthogonal Example](/diagrams/orchard-polygon.png)

So for a first pass I implement the following approach (pseudocode):

```python
```

## 3. Architecture

![Architecture](/diagrams/image.png)

## 4. Project Structure

## Journal

1. Spent time trying to understand the problem.
2. Wrote down an initial draft of functional and non-functional requirements.
3. Spent time exploring API to understand what information needs to be gathered to determine which trees are missing.
    3.1 Looked at API response shapes
    3.2 Walked through an example manually, by choosing a random orchard and walking through the steps to determine the 
        missing trees (retrieve orchard, get survey from orchard id and then call missing trees endpoint).
4. Sketched out high-level design

## Questions

1. Are we allowed to use the missing trees endpoint from 