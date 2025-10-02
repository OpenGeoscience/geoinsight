import { apiClient, getS3ffClient } from "./auth";
import {
  User,
  Project,
  ProjectPatch,
  ProjectPermissions,
  Dataset,
  Layer,
  Chart,
  AnalysisType,
  Network,
  RasterDataValues,
  FileItem,
  RasterData,
  VectorData,
  NetworkNode,
  NetworkEdge,
  LayerStyle,
  VectorSummary,
  LayerFrame,
  TaskResult,
} from "@/types";

export async function getUsers(): Promise<User[]> {
  return (await apiClient.get(`users`)).data.results;
}

export async function getProjects(): Promise<Project[]> {
  return (await apiClient.get("projects")).data.results;
}

export async function createProject(
  name: string,
  default_map_center: number[],
  default_map_zoom: number
): Promise<Project> {
  return (
    await apiClient.post("projects/", {
      name,
      default_map_center,
      default_map_zoom,
    })
  ).data;
}

export async function patchProject(
  projectId: number,
  data: ProjectPatch
): Promise<Project> {
  return (await apiClient.patch(`projects/${projectId}/`, data)).data;
}

export async function updateProjectPermissions(
  projectId: number,
  data: ProjectPermissions
): Promise<Project> {
  return (await apiClient.put(`projects/${projectId}/permissions/`, data)).data;
}

export async function deleteProject(projectId: number): Promise<Project> {
  return (await apiClient.delete(`projects/${projectId}/`)).data;
}

export async function getProjectDatasets(
  projectId: number
): Promise<Dataset[]> {
  return (await apiClient.get(`datasets?project=${projectId}`)).data.results;
}

export async function getChart(chartId: number): Promise<Chart> {
  return (await apiClient.get(`charts/${chartId}`)).data;
}

export async function getChartFiles(chartId: number): Promise<FileItem[]> {
  return (await apiClient.get(`charts/${chartId}/files`)).data;
}

export async function getProjectCharts(projectId: number): Promise<Chart[]> {
  return (await apiClient.get(`charts?project=${projectId}`)).data.results;
}

export async function getProjectAnalysisTypes(
  projectId: number
): Promise<AnalysisType[]> {
  return (await apiClient.get(`analytics/project/${projectId}/types`))
    .data;
}

export async function getDatasets(): Promise<Dataset[]> {
  return (await apiClient.get(`datasets`)).data.results;
}

export async function getDataset(datasetId: number): Promise<Dataset> {
  return (await apiClient.get(`datasets/${datasetId}`)).data;
}

export async function createDataset(data: any): Promise<Dataset> {
  return (await apiClient.post('datasets/', data)).data;
}

export async function spawnDatasetConversion(datasetId: number, options: any): Promise<Dataset> {
  return (await apiClient.post(`datasets/${datasetId}/convert/`, options || {})).data;
}

export async function getDatasetLayers(datasetId: number): Promise<Layer[]> {
  return (await apiClient.get(`datasets/${datasetId}/layers`)).data;
}

export async function getLayer(layerId: number): Promise<Layer> {
  return (await apiClient.get(`layers/${layerId}`)).data;
}

export async function getLayerFrames(layerId: number): Promise<LayerFrame[]> {
  return (await apiClient.get(`layers/${layerId}/frames`)).data;
}

export async function getDatasetFiles(datasetId: number): Promise<FileItem[]> {
  return (await apiClient.get(`datasets/${datasetId}/files`)).data;
}

export async function getFileDataObjects(fileId: number): Promise<(RasterData | VectorData)[]> {
  return (await apiClient.get(`files/${fileId}/data`)).data;
}

export async function uploadFile(file:File): Promise<string> {
  const s3ffClient = getS3ffClient()
  return await s3ffClient.uploadFile(
    file, 'core.FileItem.file',
  )
}

export async function createFileItem(data: any): Promise<FileItem> {
  return (await apiClient.post('files/', data)).data;
}

export async function getDatasetNetworks(datasetId: number): Promise<Network[]> {
  return (await apiClient.get(`datasets/${datasetId}/networks`)).data;
}

export async function getProjectNetworks(projectId: number): Promise<Network[]> {
  return (await apiClient.get(`networks/?project=${projectId}`)).data.results;
}

export async function getNetwork(networkId: number): Promise<Network> {
  return (await apiClient.get(`networks/${networkId}`)).data;
}

export async function getNetworkNodes(networkId: number, limit: number, offset: number): Promise<NetworkNode[]> {
  return (await apiClient.get(`networks/${networkId}/nodes?limit=${limit}&offset=${offset}`)).data;
}

export async function getNetworkEdges(networkId: number, limit: number, offset: number): Promise<NetworkEdge[]> {
  return (await apiClient.get(`networks/${networkId}/edges?limit=${limit}&offset=${offset}`)).data;
}

export async function getNetworkGCC(
  networkId: number,
  exclude_nodes: number[]
): Promise<number[]> {
  return (
    await apiClient.get(`networks/${networkId}/gcc?exclude_nodes=${exclude_nodes.toString()}`)
  ).data;
}

export async function getVectorSummary(vectorId: number): Promise<VectorSummary> {
  return (await apiClient.get(`vectors/${vectorId}/summary`)).data;
}

export async function getRasterDataValues(rasterId: number): Promise<RasterDataValues> {
  const resolution = 0.1;
  const data = (
    await apiClient.get(`rasters/${rasterId}/raster-data/${resolution}`)
  ).data;
  const { bounds } = (await apiClient.get(`rasters/${rasterId}/info/metadata`))
    .data;
  return {
    data,
    sourceBounds: bounds,
  };
}

export async function runAnalysis(
  analysisType: string,
  projectId: number,
  args: object
) {
  return (
    await apiClient.post(
      `analytics/project/${projectId}/types/${analysisType}/run/`,
      args
    )
  ).data;
}

export async function getTaskResults(
  analysisType: string,
  projectId: number
) {
  return (
    await apiClient.get(
      `analytics/project/${projectId}/types/${analysisType}/results/`
    )
  ).data;
}

export async function getTaskResult(resultId: number): Promise<TaskResult> {
  return (await apiClient.get(`analytics/${resultId}`)).data;
}

export async function getVectorDataBounds(vectorId: number): Promise<number[]> {
  return (await apiClient.get(`vectors/${vectorId}/bounds`)).data;
}

export async function getLayerStyles(layerId: number): Promise<LayerStyle[]> {
  return (await apiClient.get(`layer-styles/?layer=${layerId}`)).data.results;
}

export async function createLayerStyle(data: LayerStyle): Promise<LayerStyle> {
  return (await apiClient.post('layer-styles/', data)).data;
}

export async function updateLayerStyle(styleId: number, data: LayerStyle): Promise<LayerStyle> {
  return (await apiClient.patch(`layer-styles/${styleId}/`, data)).data;
}

export async function deleteLayerStyle(styleId: number): Promise<LayerStyle> {
  return (await apiClient.delete(`layer-styles/${styleId}/`)).data;
}
