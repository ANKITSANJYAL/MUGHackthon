import { GoogleGenAI } from "@google/genai";
import { PROPOSAL } from "../constants";

const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

export const analyzeArchitecture = async (focus: 'bottleneck' | 'security' | 'summary'): Promise<string> => {
  if (!apiKey) {
    return "API Key is missing. Please configure process.env.API_KEY.";
  }

  const modelId = "gemini-2.5-flash";
  
  let prompt = "";
  const context = JSON.stringify(PROPOSAL);

  switch (focus) {
    case 'bottleneck':
      prompt = `Analyze the following software architecture proposal JSON. Identify 3 potential performance bottlenecks or failure points in the workflow. Be concise. \n\n${context}`;
      break;
    case 'security':
      prompt = `Analyze the following software architecture proposal JSON. Identify 3 potential security risks, specifically regarding the integration of internal proprietary data (MongoDB) and external AI tools. Be concise. \n\n${context}`;
      break;
    case 'summary':
    default:
      prompt = `Provide a high-level executive summary (max 3 sentences) of why this "Hybrid Knowledge Fixer" architecture is effective for consulting firms. \n\n${context}`;
      break;
  }

  try {
    const response = await ai.models.generateContent({
      model: modelId,
      contents: prompt,
      config: {
        thinkingConfig: { thinkingBudget: 0 } 
      }
    });
    return response.text || "No response generated.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "Failed to analyze architecture. Check console for details.";
  }
};
