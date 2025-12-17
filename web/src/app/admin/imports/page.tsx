"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { uploadCSV, startImport, getImportStatus, listImports } from "../../../lib/api";
import { ImportUploadResponse, AdminImport } from "../../../lib/types";

type ImportStep = "upload" | "mapping" | "processing" | "complete";

const TARGET_FIELDS = [
  { value: "", label: "-- Skip --" },
  { value: "url", label: "URL (required)" },
  { value: "external_id", label: "External ID / Lot Number" },
  { value: "title", label: "Title / Description" },
  { value: "year", label: "Year" },
  { value: "make", label: "Make / Manufacturer" },
  { value: "model", label: "Model" },
  { value: "price", label: "Price / Current Bid" },
  { value: "mileage", label: "Mileage / Odometer" },
  { value: "location", label: "Location / Sale Name" },
  { value: "sale_date", label: "Sale Date / Auction Date" },
  { value: "vin", label: "VIN" },
  { value: "damage", label: "Damage Description" },
  { value: "title_code", label: "Title Code / Status" },
  { value: "retail_value", label: "Retail Value / Est. Value" },
];

export default function ImportsPage() {
  const [step, setStep] = useState<ImportStep>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResponse, setUploadResponse] = useState<ImportUploadResponse | null>(null);
  const [columnMap, setColumnMap] = useState<Record<string, string>>({});
  const [sourceKey, setSourceKey] = useState("copart_manual");
  const [importStatus, setImportStatus] = useState<AdminImport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [recentImports, setRecentImports] = useState<AdminImport[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load recent imports on mount
  useEffect(() => {
    loadRecentImports();
  }, []);

  const loadRecentImports = async () => {
    try {
      const data = await listImports(10);
      setRecentImports(data);
    } catch (e: any) {
      console.error("Failed to load recent imports:", e);
    }
  };

  // Poll import status
  useEffect(() => {
    if (step === "processing" && uploadResponse) {
      pollingIntervalRef.current = setInterval(async () => {
        try {
          const status = await getImportStatus(uploadResponse.import_id);
          setImportStatus(status);

          if (status.status === "SUCCEEDED" || status.status === "FAILED") {
            setStep("complete");
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
            }
            loadRecentImports();
          }
        } catch (e: any) {
          console.error("Failed to poll status:", e);
        }
      }, 2000); // Poll every 2 seconds

      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
      };
    }
  }, [step, uploadResponse]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile.name.endsWith(".csv")) {
      setError("Please select a CSV file");
      return;
    }
    setFile(selectedFile);
    setError(null);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      handleFileSelect(files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const response = await uploadCSV(file, sourceKey);
      setUploadResponse(response);
      setColumnMap(response.suggested_mapping);
      setStep("mapping");
    } catch (e: any) {
      setError(e.message || "Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  const handleStartImport = async () => {
    if (!uploadResponse) return;

    // Validate that URL is mapped
    const mappedFields = Object.values(columnMap);
    if (!mappedFields.includes("url")) {
      setError("Required field 'URL' must be mapped");
      return;
    }

    setError(null);

    try {
      await startImport(uploadResponse.import_id, {
        column_map: columnMap,
        source_key: sourceKey,
      });
      setStep("processing");
    } catch (e: any) {
      setError(e.message || "Failed to start import");
    }
  };

  const handleReset = () => {
    setStep("upload");
    setFile(null);
    setUploadResponse(null);
    setColumnMap({});
    setImportStatus(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">CSV Imports</h1>
        <p className="text-sm text-slate-400">Upload and import vehicle listings from CSV files</p>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {/* Upload Step */}
      {step === "upload" && (
        <Card>
          <CardHeader>
            <CardTitle>Upload CSV File</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? "border-blue-500 bg-blue-500/10"
                  : "border-slate-700 hover:border-slate-600"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <div className="space-y-3">
                <div className="text-4xl">📁</div>
                <div>
                  <p className="text-lg">Drag and drop your CSV file here</p>
                  <p className="text-sm text-slate-400 mt-1">or click to browse</p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileInputChange}
                  className="hidden"
                  id="file-upload"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                >
                  Select File
                </Button>
              </div>
            </div>

            {file && (
              <div className="bg-slate-800 rounded p-3 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">📄</div>
                  <div>
                    <div className="font-medium">{file.name}</div>
                    <div className="text-xs text-slate-400">{formatBytes(file.size)}</div>
                  </div>
                </div>
                <Button
                  onClick={() => {
                    setFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  variant="outline"
                  size="sm"
                >
                  Remove
                </Button>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Source Key (Optional)</label>
              <input
                type="text"
                value={sourceKey}
                onChange={(e) => setSourceKey(e.target.value)}
                placeholder="e.g., copart_manual"
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
              />
              <p className="text-xs text-slate-400">
                Identifier for this import source (used for deduplication and tracking)
              </p>
            </div>

            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full"
            >
              {uploading ? "Uploading..." : "Upload and Preview"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Mapping Step */}
      {step === "mapping" && uploadResponse && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Preview and Map Columns</CardTitle>
              <div className="text-sm text-slate-400 mt-1">
                {uploadResponse.total_rows.toLocaleString()} rows detected
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-slate-400">
                Map CSV columns to target fields. At minimum, map the URL column.
              </div>

              <div className="space-y-2 max-h-96 overflow-y-auto">
                {uploadResponse.detected_headers.map((header) => (
                  <div key={header} className="flex items-center space-x-3 bg-slate-800 p-3 rounded">
                    <div className="flex-1 font-mono text-sm">{header}</div>
                    <div className="text-slate-500">→</div>
                    <select
                      value={columnMap[header] || ""}
                      onChange={(e) => setColumnMap({ ...columnMap, [header]: e.target.value })}
                      className="bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm min-w-[200px]"
                    >
                      {TARGET_FIELDS.map((field) => (
                        <option key={field.value} value={field.value}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              {/* Preview Table */}
              <div className="border border-slate-700 rounded overflow-hidden">
                <div className="text-sm font-medium p-2 bg-slate-800">
                  Preview (first 5 rows)
                </div>
                <div className="overflow-x-auto max-h-64">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-900 sticky top-0">
                      <tr>
                        {uploadResponse.detected_headers.map((header) => (
                          <th key={header} className="px-2 py-2 text-left font-medium whitespace-nowrap">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {uploadResponse.sample_preview.slice(0, 5).map((row, idx) => (
                        <tr key={idx} className="border-t border-slate-800">
                          {uploadResponse.detected_headers.map((header) => (
                            <td key={header} className="px-2 py-1.5 whitespace-nowrap">
                              {row[header] || "-"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex space-x-3">
                <Button onClick={handleReset} variant="outline">
                  Cancel
                </Button>
                <Button onClick={handleStartImport} className="flex-1">
                  Start Import ({uploadResponse.total_rows.toLocaleString()} rows)
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Processing Step */}
      {step === "processing" && importStatus && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Import</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>
                  {importStatus.processed_rows} / {importStatus.total_rows || 0} rows
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-blue-600 h-full transition-all duration-300"
                  style={{
                    width: `${
                      importStatus.total_rows
                        ? (importStatus.processed_rows / importStatus.total_rows) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-4 gap-3 text-sm">
              <div className="bg-green-900/20 border border-green-800 rounded p-3">
                <div className="text-green-400 text-xl font-bold">{importStatus.created_count}</div>
                <div className="text-slate-400">Created</div>
              </div>
              <div className="bg-blue-900/20 border border-blue-800 rounded p-3">
                <div className="text-blue-400 text-xl font-bold">{importStatus.updated_count}</div>
                <div className="text-slate-400">Updated</div>
              </div>
              <div className="bg-slate-800 border border-slate-700 rounded p-3">
                <div className="text-slate-400 text-xl font-bold">{importStatus.skipped_count}</div>
                <div className="text-slate-400">Skipped</div>
              </div>
              <div className="bg-red-900/20 border border-red-800 rounded p-3">
                <div className="text-red-400 text-xl font-bold">{importStatus.error_count}</div>
                <div className="text-slate-400">Errors</div>
              </div>
            </div>

            <div className="text-center text-sm text-slate-400">
              Processing... This may take a few minutes for large files.
            </div>
          </CardContent>
        </Card>
      )}

      {/* Complete Step */}
      {step === "complete" && importStatus && (
        <Card>
          <CardHeader>
            <CardTitle className={importStatus.status === "SUCCEEDED" ? "text-green-400" : "text-red-400"}>
              {importStatus.status === "SUCCEEDED" ? "Import Complete ✓" : "Import Failed ✗"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-4 gap-3 text-sm">
              <div className="bg-green-900/20 border border-green-800 rounded p-3">
                <div className="text-green-400 text-xl font-bold">{importStatus.created_count}</div>
                <div className="text-slate-400">Created</div>
              </div>
              <div className="bg-blue-900/20 border border-blue-800 rounded p-3">
                <div className="text-blue-400 text-xl font-bold">{importStatus.updated_count}</div>
                <div className="text-slate-400">Updated</div>
              </div>
              <div className="bg-slate-800 border border-slate-700 rounded p-3">
                <div className="text-slate-400 text-xl font-bold">{importStatus.skipped_count}</div>
                <div className="text-slate-400">Skipped</div>
              </div>
              <div className="bg-red-900/20 border border-red-800 rounded p-3">
                <div className="text-red-400 text-xl font-bold">{importStatus.error_count}</div>
                <div className="text-slate-400">Errors</div>
              </div>
            </div>

            {importStatus.error_log && (
              <div className="bg-slate-900 border border-slate-700 rounded p-3">
                <div className="text-sm font-medium mb-2">Error Log:</div>
                <pre className="text-xs text-red-400 overflow-x-auto max-h-48">
                  {importStatus.error_log}
                </pre>
              </div>
            )}

            <div className="flex space-x-3">
              <Button onClick={handleReset} className="flex-1">
                Import Another File
              </Button>
              <Button
                onClick={() => window.location.href = "/search"}
                variant="outline"
              >
                View in Search
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Imports */}
      {step === "upload" && recentImports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Imports</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentImports.map((imp) => (
                <div key={imp.id} className="bg-slate-800 rounded p-3 flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-sm">{imp.filename}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      {formatDate(imp.created_at)} • {imp.total_rows?.toLocaleString()} rows
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        imp.status === "SUCCEEDED"
                          ? "bg-green-900/30 text-green-400"
                          : imp.status === "FAILED"
                          ? "bg-red-900/30 text-red-400"
                          : imp.status === "RUNNING"
                          ? "bg-blue-900/30 text-blue-400"
                          : "bg-slate-700 text-slate-400"
                      }`}
                    >
                      {imp.status}
                    </div>
                    <div className="text-xs text-slate-400">
                      {imp.created_count} created
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
