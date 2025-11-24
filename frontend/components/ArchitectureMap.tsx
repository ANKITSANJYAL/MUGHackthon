import React from 'react';
import { NodePosition, Edge } from '../types';

interface ArchitectureMapProps {
  nodes: NodePosition[];
  edges: Edge[];
  activeStep: number;
  onNodeClick: (node: NodePosition) => void;
  selectedNodeId: string | null;
}

const ArchitectureMap: React.FC<ArchitectureMapProps> = ({ 
  nodes, 
  edges, 
  activeStep, 
  onNodeClick, 
  selectedNodeId 
}) => {
  
  // Helper to determine edge color based on active simulation step
  const getEdgeColor = (edge: Edge) => {
    const isActive = edge.activeInStep?.includes(activeStep);
    return isActive ? '#60A5FA' : '#334155'; // Blue-400 vs Slate-700
  };

  const getEdgeWidth = (edge: Edge) => {
    return edge.activeInStep?.includes(activeStep) ? 3 : 1;
  };

  const getEdgeClass = (edge: Edge) => {
    return edge.activeInStep?.includes(activeStep) ? 'animate-pulse' : '';
  };

  // Helper to draw curved paths between nodes (percentage based coordinates)
  const drawPath = (edge: Edge) => {
    const fromNode = nodes.find(n => n.id === edge.from);
    const toNode = nodes.find(n => n.id === edge.to);
    
    if (!fromNode || !toNode) return '';

    // Convert percentage to viewbox coordinates (assuming 1000x1000 viewbox for easier math)
    const x1 = fromNode.x * 10;
    const y1 = fromNode.y * 10;
    const x2 = toNode.x * 10;
    const y2 = toNode.y * 10;

    // Bezier control points
    const dx = x2 - x1;
    const dy = y2 - y1;
    const controlX1 = x1 + dx * 0.1; 
    const controlY1 = y1 + dy * 0.5;
    const controlX2 = x2 - dx * 0.1;
    const controlY2 = y2 - dy * 0.5;

    return `M ${x1} ${y1} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${x2} ${y2}`;
  };

  return (
    <div className="relative w-full h-full bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden group">
      {/* Grid Background */}
      <div className="absolute inset-0 opacity-10 pointer-events-none" 
           style={{ 
             backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', 
             backgroundSize: '30px 30px' 
           }}>
      </div>

      {/* SVG Layer for Edges */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" viewBox="0 0 1000 1000" preserveAspectRatio="none">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="28" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748B" />
          </marker>
          <marker id="arrowhead-active" markerWidth="10" markerHeight="7" refX="28" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#60A5FA" />
          </marker>
        </defs>
        {edges.map((edge, idx) => (
          <g key={`${edge.from}-${edge.to}-${idx}`}>
            <path
              d={drawPath(edge)}
              fill="none"
              stroke={getEdgeColor(edge)}
              strokeWidth={getEdgeWidth(edge)}
              className={`transition-all duration-500 ${getEdgeClass(edge)}`}
              markerEnd={edge.activeInStep?.includes(activeStep) ? "url(#arrowhead-active)" : "url(#arrowhead)"}
            />
          </g>
        ))}
      </svg>

      {/* Nodes Layer */}
      {nodes.map((node) => {
        const isSelected = selectedNodeId === node.id;
        
        let bgColor = 'bg-slate-800';
        let borderColor = 'border-slate-600';
        
        if (node.type === 'core') { borderColor = 'border-purple-500'; bgColor = 'bg-slate-800'; }
        if (node.type === 'knowledge') { borderColor = 'border-mongo'; } // mongo green
        if (node.id === 'tavily') { borderColor = 'border-tavily'; } // tavily blue
        if (isSelected) { bgColor = 'bg-slate-700'; borderColor = 'border-white'; }

        return (
          <div
            key={node.id}
            onClick={() => onNodeClick(node)}
            className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer
                        w-32 h-24 md:w-40 md:h-28 flex flex-col items-center justify-center p-2 rounded-xl border-2 
                        transition-all duration-300 hover:scale-110 hover:shadow-[0_0_20px_rgba(255,255,255,0.1)] z-10
                        ${bgColor} ${borderColor} ${isSelected ? 'shadow-[0_0_30px_rgba(255,255,255,0.2)]' : 'shadow-lg'}`}
            style={{ left: `${node.x}%`, top: `${node.y}%` }}
          >
            <div className="text-3xl mb-1">{node.icon}</div>
            <div className="text-xs md:text-sm font-bold text-center text-slate-200 leading-tight">
              {node.label}
            </div>
            {node.type === 'knowledge' && (
              <div className="absolute -top-2 -right-2 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            )}
          </div>
        );
      })}
      
      <div className="absolute bottom-4 left-4 text-xs text-slate-500 font-mono">
        H-KFX Architecture v1.0
      </div>
    </div>
  );
};

export default ArchitectureMap;
