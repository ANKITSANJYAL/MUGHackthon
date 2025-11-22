import os
import logging
import subprocess
import tempfile
import shutil
import re
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ComprehensiveAnalysisAgent:
    """Comprehensive agent that clones, builds, tests, and analyzes issues."""

    def __init__(self):
        self.work_dir = None
        self.client = None
        if OpenAI and os.getenv("OPENAI_API_KEY"):
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _run_command(self, cmd: List[str], timeout: int = 60, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run a shell command and capture output."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:1000],
                "success": result.returncode == 0,
                "command": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timeout after {timeout}s",
                "success": False,
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "command": " ".join(cmd)
            }

    def _clone_repo(self, repo_url: str) -> bool:
        """Clone the GitHub repository."""
        self.work_dir = tempfile.mkdtemp(prefix="jiae_analysis_")
        try:
            result = self._run_command(["git", "clone", repo_url, self.work_dir], timeout=60, cwd="/tmp")
            if result["success"]:
                logger.info(f"✓ Repository cloned to {self.work_dir}")
                return True
            else:
                logger.error(f"Clone failed: {result['stderr']}")
                return False
        except Exception as e:
            logger.error(f"Clone exception: {e}")
            return False

    def _detect_project_type(self) -> Dict[str, Any]:
        """Detect the project type based on files present."""
        detection = {
            "python": False,
            "javascript": False,
            "java": False,
            "go": False,
            "rust": False,
            "cpp": False,
            "build_files": [],
            "detected_types": []
        }

        if not self.work_dir or not os.path.exists(self.work_dir):
            return detection

        for root, dirs, files in os.walk(self.work_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git']]
            
            for file in files:
                if file in ['package.json', 'package-lock.json', 'yarn.lock']:
                    detection["javascript"] = True
                    detection["build_files"].append(file)
                elif file in ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile']:
                    detection["python"] = True
                    detection["build_files"].append(file)
                elif file in ['pom.xml', 'build.gradle', 'settings.gradle']:
                    detection["java"] = True
                    detection["build_files"].append(file)
                elif file in ['go.mod', 'go.sum']:
                    detection["go"] = True
                    detection["build_files"].append(file)
                elif file in ['Cargo.toml', 'Cargo.lock']:
                    detection["rust"] = True
                    detection["build_files"].append(file)
                elif file in ['CMakeLists.txt', 'Makefile']:
                    detection["cpp"] = True
                    detection["build_files"].append(file)

        if detection["javascript"]:
            detection["detected_types"].append("JavaScript/Node.js")
        if detection["python"]:
            detection["detected_types"].append("Python")
        if detection["java"]:
            detection["detected_types"].append("Java")
        if detection["go"]:
            detection["detected_types"].append("Go")
        if detection["rust"]:
            detection["detected_types"].append("Rust")
        if detection["cpp"]:
            detection["detected_types"].append("C++")

        return detection

    def _analyze_with_ai(self, issue_description: str, project_info: str) -> Dict[str, Any]:
        """Use AI to determine what commands to run."""
        if not self.client:
            return {"error": "OpenAI not configured"}

        prompt = f"""You are a software expert. Based on this issue and project, suggest diagnostic commands.

ISSUE: {issue_description}
PROJECT: {project_info}

Return JSON:
{{"issue_category":"build|runtime|import|syntax|dependency|test|other","severity":"critical|high|medium|low","root_cause_hypothesis":"Your hypothesis","diagnostic_commands":[{{"command":"npm install","description":"Install dependencies"}}],"recommendations":["rec1","rec2"]}}"""

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            
            response_text = response.choices[0].message.content.strip()
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            if not response_text:
                return {"error": "Empty response from AI"}
            
            result = json.loads(response_text)
            return result
            
        except json.JSONDecodeError as je:
            logger.error(f"JSON parse error: {str(je)}")
            return {"error": f"Invalid JSON: {str(je)}"}
        except Exception as e:
            logger.error(f"AI error: {str(e)}")
            return {"error": str(e)}

    def _run_diagnostic_commands(self, commands: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Run diagnostic commands suggested by AI."""
        results = []
        for cmd_obj in commands:
            cmd_str = cmd_obj.get("command", "")
            if not cmd_str:
                continue
                
            print(f"  �� Running: {cmd_str}")
            result = self._run_command(cmd_str.split(), timeout=120)
            result["description"] = cmd_obj.get("description", "")
            results.append(result)
            
            if result["success"]:
                print(f"    ✅ Success")
            else:
                print(f"    ❌ Failed")
        
        return results

    def analyze_issue(self, issue_key: str, issue_description: str, repo_url: str) -> Dict[str, Any]:
        """Main analysis workflow."""
        print(f"\n{'='*80}")
        print(f"🚀 COMPREHENSIVE ANALYSIS - ISSUE {issue_key}")
        print(f"{'='*80}")

        result = {
            "issue_key": issue_key,
            "status": "UNKNOWN",
            "project_detection": {},
            "diagnostic_results": [],
            "final_analysis": ""
        }

        try:
            print("📥 Cloning repository...")
            if not self._clone_repo(repo_url):
                result["status"] = "CLONE_FAILED"
                return result

            print("🔎 Detecting project type...")
            project_detection = self._detect_project_type()
            result["project_detection"] = project_detection
            print(f"   Detected: {', '.join(project_detection['detected_types']) or 'Unknown'}")

            print("🧠 Generating diagnostic strategy...")
            ai_strategy = self._analyze_with_ai(issue_description, str(project_detection))
            
            if "error" not in ai_strategy and "diagnostic_commands" in ai_strategy:
                print(f"\n🔧 Running diagnostic commands...")
                diagnostic_results = self._run_diagnostic_commands(ai_strategy["diagnostic_commands"])
                result["diagnostic_results"] = diagnostic_results
                
                has_errors = any(not r["success"] for r in diagnostic_results)
                if has_errors:
                    result["status"] = "ISSUE_VERIFIED"
                    result["final_analysis"] = "Issue verified - errors found during build/test"
                else:
                    result["status"] = "ISSUE_NOT_FOUND"
                    result["final_analysis"] = "No errors found"
            else:
                result["status"] = "ANALYSIS_ERROR"
                result["final_analysis"] = ai_strategy.get("error", "Unknown error")

            print(f"\n{'='*80}")
            print(f"🎯 Status: {result['status']}")
            print(f"{'='*80}\n")
            return result

        except Exception as e:
            logger.exception("Analysis failed")
            result["status"] = "ANALYSIS_ERROR"
            result["final_analysis"] = str(e)
            return result

        finally:
            if self.work_dir and os.path.exists(self.work_dir):
                try:
                    shutil.rmtree(self.work_dir)
                except Exception as e:
                    logger.error(f"Cleanup failed: {e}")
