from __future__ import annotations

from django.contrib.gis.db import models as geo_models
from django.db import connection, models

from .data import VectorData, VectorFeature
from .querysets import ProjectQuerySet

GCC_QUERY = """
WITH RECURSIVE n as (
    -- starting node
    SELECT id FROM (
        SELECT cnn.id
        FROM core_networknode cnn
        WHERE
            cnn.network_id = %(network_id)s AND
            NOT (cnn.id = ANY(%(excluded_nodes)s))
        ORDER BY random()
        LIMIT 1
    ) nn
    UNION
    -- Select the *other* node in the edge
    SELECT CASE
        WHEN e.to_node_id = n.id
        THEN e.from_node_id
        ELSE e.to_node_id
    END
    FROM n
    JOIN (
        SELECT *
        FROM core_networkedge ne
        WHERE
            ne.network_id = %(network_id)s AND
            NOT (
                ne.from_node_id = ANY(%(excluded_nodes)s) OR
                ne.to_node_id = ANY(%(excluded_nodes)s)
            )
    ) e
    ON
        e.from_node_id = n.id OR
        e.to_node_id = n.id
)
SELECT id FROM n ORDER BY id
;
"""

GCC_QUERY_ITERATION_THRESHOLD = 50


class Network(models.Model):
    name = models.CharField(max_length=255, default="Network")
    vector_data = models.ForeignKey(VectorData, on_delete=models.CASCADE, related_name="networks")
    category = models.CharField(max_length=25)
    metadata = models.JSONField(blank=True, null=True)

    project_filter_path = "vector_data__dataset__project"
    objects = ProjectQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.id})"

    @property
    def dataset(self):
        return self.vector_data.dataset

    def get_gcc(self, excluded_nodes: list[int]):
        total_nodes = NetworkNode.objects.filter(network=self).count()

        # This is used to store all the nodes we've already visited,
        # starting with the explicitly excluded nodes
        cur_excluded_nodes = excluded_nodes.copy()

        # Store largest network found so far
        gcc: list[int] = []

        # Track the number of iterations, aborting if this reaches some threshold
        iterations = 0

        with connection.cursor() as cursor:
            # If the GCC size is greater than half the network, we know that there's no way to
            # find a larger one. If we've exhausted all nodes, also stop searching.
            while not (len(gcc) > (total_nodes // 2) or len(cur_excluded_nodes) >= total_nodes):
                cursor.execute(
                    GCC_QUERY,
                    {
                        "excluded_nodes": cur_excluded_nodes,
                        "network_id": self.pk,
                    },
                )
                nodes: list[int] = [x[0] for x in cursor.fetchall()]
                if not nodes:
                    raise RuntimeError("Expected to find nodes but found none")

                cur_excluded_nodes.extend(nodes)
                if len(nodes) > len(gcc):
                    gcc = nodes

                iterations += 1
                if iterations > GCC_QUERY_ITERATION_THRESHOLD:
                    return None

        return gcc


class NetworkNode(models.Model):
    name = models.CharField(max_length=255)
    vector_feature = models.ForeignKey(
        VectorFeature, on_delete=models.CASCADE, related_name="nodes", null=True
    )
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="nodes")
    metadata = models.JSONField(blank=True, null=True)
    capacity = models.IntegerField(null=True)
    location = geo_models.PointField()

    project_filter_path = "network__vector_data__dataset__project"
    objects = ProjectQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.id})"

    @property
    def dataset(self):
        return self.network.dataset

    def get_adjacent_nodes(self) -> models.QuerySet:
        entering_node_ids = (
            NetworkEdge.objects.filter(to_node=self.id)
            .values_list("from_node_id", flat=True)
            .distinct()
        )
        exiting_node_ids = (
            NetworkEdge.objects.filter(from_node=self.id)
            .values_list("to_node_id", flat=True)
            .distinct()
        )
        return NetworkNode.objects.exclude(id=self.id).filter(
            models.Q(id__in=entering_node_ids) | models.Q(id__in=exiting_node_ids)
        )


class NetworkEdge(models.Model):
    name = models.CharField(max_length=255)
    vector_feature = models.ForeignKey(
        VectorFeature, on_delete=models.CASCADE, related_name="edges", null=True
    )
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="edges")
    metadata = models.JSONField(blank=True, null=True)
    capacity = models.IntegerField(null=True)
    line_geometry = geo_models.LineStringField()
    directed = models.BooleanField(default=False)
    from_node = models.ForeignKey(NetworkNode, related_name="+", on_delete=models.CASCADE)
    to_node = models.ForeignKey(NetworkNode, related_name="+", on_delete=models.CASCADE)

    project_filter_path = "network__vector_data__dataset__project"
    objects = ProjectQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.id})"

    @property
    def dataset(self):
        return self.network.dataset
