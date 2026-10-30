package datamarts;

public record MongoStorageStats(long documents, long dataBytes, long storageBytes, long indexBytes) {
}
