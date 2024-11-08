import React, { useState, useRef, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Alert, AlertDescription } from './ui/alert';
import { Button } from './ui/button';
import { ZoomIn, ZoomOut, Move } from 'lucide-react';

const_API_URL = 'https://batch-depmap-and-biogrid.onrender.com';

const GeneNetworkVisualizer = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  useEffect(() => {
    checkServerStatus();
  }, []);

  const checkServerStatus = async () => {
    try {
      const response = await fetch('https://batch-depmap-and-biogrid.onrender.com/status/');
      if (!response.ok) throw new Error('Server status check failed');
      const status = await response.json();
      setServerStatus(status);
    } catch (err) {
      setError('Could not connect to server: ' + err.message);
    }
  };

  const processFile = async (file) => {
    if (!file) {
      setError('Please upload a genes file');
      return;
    }

    setIsProcessing(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('genes_file', file);

      const response = await fetch('https://batch-depmap-and-biogrid.onrender.com/upload/', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Network processing failed');
      }

      const networkData = await response.json();
      
      // Create node positions in a circle
      const radius = 200;
      const centerX = 300;
      const centerY = 250;
      
      const nodePositions = networkData.nodes.map((node, i) => ({
        ...node,
        x: centerX + radius * Math.cos((i / networkData.nodes.length) * 2 * Math.PI),
        y: centerY + radius * Math.sin((i / networkData.nodes.length) * 2 * Math.PI),
        labelOffset: { x: 0, y: 20 }
      }));

      setNodes(nodePositions);
      setEdges(networkData.edges);

    } catch (err) {
      setError(`Error processing file: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = -e.deltaY;
    const scaleChange = delta > 0 ? 1.1 : 0.9;
    const newScale = Math.max(0.1, Math.min(5, transform.scale * scaleChange));
    setTransform(prev => ({ ...prev, scale: newScale }));
  };

  const handleMouseDown = (e) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - transform.x,
        y: e.clientY - transform.y
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setTransform(prev => ({
        ...prev,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      }));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const zoomIn = () => {
    setTransform(prev => ({
      ...prev,
      scale: Math.min(5, prev.scale * 1.2)
    }));
  };

  const zoomOut = () => {
    setTransform(prev => ({
      ...prev,
      scale: Math.max(0.1, prev.scale / 1.2)
    }));
  };

  const resetView = () => {
    setTransform({ x: 0, y: 0, scale: 1 });
  };

  return (
    <Card className="w-full max-w-4xl mx-auto m-4">
      <CardHeader>
        <CardTitle>Gene Network Visualizer</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {serverStatus && (
            <div className="space-y-2">
              <Alert variant={serverStatus.links_file_loaded ? "default" : "destructive"}>
                <AlertDescription>
                  Links file: {serverStatus.links_file_loaded ? 
                    `Loaded (${serverStatus.links_file_rows.toLocaleString()} rows)` : 
                    "Not loaded"}
                </AlertDescription>
              </Alert>
              <Alert variant={serverStatus.biogrid_file_loaded ? "default" : "destructive"}>
                <AlertDescription>
                  BioGrid file: {serverStatus.biogrid_file_loaded ? 
                    `Loaded (${serverStatus.biogrid_file_rows.toLocaleString()} rows)` : 
                    "Not loaded"}
                </AlertDescription>
              </Alert>
            </div>
          )}

          <div>
            <h3 className="text-sm font-medium mb-2">Upload Genes of Interest File (.xlsx)</h3>
            <Input
              type="file"
              accept=".xlsx"
              onChange={(e) => processFile(e.target.files[0])}
              className="flex-1"
              disabled={isProcessing || !serverStatus?.links_file_loaded || !serverStatus?.biogrid_file_loaded}
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {isProcessing && (
            <Alert>
              <AlertDescription>Processing network data...</AlertDescription>
            </Alert>
          )}

          {nodes.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm" onClick={zoomIn}>
                  <ZoomIn className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={zoomOut}>
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={resetView}>
                  Reset View
                </Button>
                <Move className="w-4 h-4 ml-2 text-gray-500" />
                <span className="text-sm text-gray-500">Drag to pan</span>
              </div>

              <div className="border rounded-lg overflow-hidden bg-white p-4">
                <svg 
                  width="600" 
                  height="500" 
                  className="w-full cursor-move"
                  ref={svgRef}
                  onWheel={handleWheel}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                >
                  <g transform={`translate(${transform.x},${transform.y}) scale(${transform.scale})`}>
                    {edges.map((edge, i) => {
                      const sourceNode = nodes.find(n => n.id === edge.source);
                      const targetNode = nodes.find(n => n.id === edge.target);
                      if (sourceNode && targetNode) {
                        return (
                          <line
                            key={`edge-${i}`}
                            x1={sourceNode.x}
                            y1={sourceNode.y}
                            x2={targetNode.x}
                            y2={targetNode.y}
                            stroke={edge.isBiogrid ? '#9333ea' : (edge.value >= 0 ? '#22c55e' : '#ef4444')}
                            strokeWidth={edge.isBiogrid ? 1 : Math.abs(edge.value) * 2}
                            opacity={0.6}
                          />
                        );
                      }
                      return null;
                    })}
                    
                    {nodes.map((node, i) => (
                      <g key={`node-${i}`}>
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r={6}
                          fill={node.isInterest ? '#22c55e' : '#94a3b8'}
                          className="cursor-pointer hover:opacity-80"
                        />
                        <text
                          x={node.x + node.labelOffset.x}
                          y={node.y + node.labelOffset.y}
                          textAnchor="middle"
                          className="text-xs fill-current"
                        >
                          {node.id}
                        </text>
                      </g>
                    ))}
                  </g>

                  <g transform="translate(20, 420)">
                    <rect width="240" height="70" fill="white" opacity="0.9"/>
                    <circle cx="15" cy="15" r={6} fill="#22c55e"/>
                    <text x="30" y="19" className="text-xs">Genes of Interest</text>
                    <circle cx="15" cy="35" r={6} fill="#94a3b8"/>
                    <text x="30" y="39" className="text-xs">Other Genes</text>
                    <line x1="10" y1="55" x2="20" y2="55" stroke="#22c55e" strokeWidth="2"/>
                    <text x="30" y="59" className="text-xs">Positive Correlation</text>
                    <line x1="120" y1="55" x2="130" y2="55" stroke="#ef4444" strokeWidth="2"/>
                    <text x="140" y="59" className="text-xs">Negative Correlation</text>
                  </g>
                </svg>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default GeneNetworkVisualizer;
