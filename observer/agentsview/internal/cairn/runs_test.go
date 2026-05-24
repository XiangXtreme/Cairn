package cairn

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestListRunsParsesSkillMetadata(t *testing.T) {
	root := t.TempDir()
	projectDir := filepath.Join(root, "proj_001")
	if err := os.MkdirAll(projectDir, 0o755); err != nil {
		t.Fatalf("mkdir project dir: %v", err)
	}
	data := `{
  "schema_version": 1,
  "run_id": "run_1",
  "project_id": "proj_001",
  "phase": "reason_execute",
  "worker_name": "codex_main",
  "agent_type": "codex",
  "workspace_name": "proj_001",
  "workspace_path": "/tmp/proj_001",
  "status": "success",
  "started_at": "2026-05-18T00:00:00Z",
  "updated_at": "2026-05-18T00:00:01Z",
  "timed_out": false,
  "cancelled": false,
  "stdout_preview": "",
  "stderr_preview": "",
  "skill_ids": ["cairn-web-surface", "cairn-creds-smb"],
  "skill_names": ["Cairn Web Surface", "Cairn Creds SMB"],
  "skill_source_paths": ["/repo/skills/cairn-web-surface", "/repo/skills/cairn-creds-smb"]
}`
	if err := os.WriteFile(filepath.Join(projectDir, "run_1.json"), []byte(data), 0o644); err != nil {
		t.Fatalf("write run json: %v", err)
	}

	runs, err := ListRuns(context.Background(), root, ListFilter{})
	if err != nil {
		t.Fatalf("ListRuns: %v", err)
	}
	if len(runs) != 1 {
		t.Fatalf("expected 1 run, got %d", len(runs))
	}
	if got, want := len(runs[0].SkillIDs), 2; got != want {
		t.Fatalf("SkillIDs len: got %d want %d", got, want)
	}
	if runs[0].SkillNames[0] != "Cairn Web Surface" {
		t.Fatalf("unexpected first skill name: %q", runs[0].SkillNames[0])
	}
	if runs[0].SkillSourcePaths[1] != "/repo/skills/cairn-creds-smb" {
		t.Fatalf("unexpected second skill path: %q", runs[0].SkillSourcePaths[1])
	}
}

func TestListRunsNormalizesLegacySessionID(t *testing.T) {
	root := t.TempDir()
	projectDir := filepath.Join(root, "proj_001")
	if err := os.MkdirAll(projectDir, 0o755); err != nil {
		t.Fatalf("mkdir project dir: %v", err)
	}
	data := `{
  "schema_version": 1,
  "run_id": "run_legacy",
  "project_id": "proj_001",
  "phase": "bootstrap",
  "worker_name": "codex_main",
  "agent_type": "codex",
  "workspace_name": "proj_001",
  "workspace_path": "/tmp/proj_001",
  "session_id": "019e5849-4460-7423-80c6-f39351b39992",
  "status": "success",
  "started_at": "2026-05-24T04:40:56Z",
  "updated_at": "2026-05-24T04:41:33Z",
  "timed_out": false,
  "cancelled": false,
  "stdout_preview": "",
  "stderr_preview": ""
}`
	if err := os.WriteFile(filepath.Join(projectDir, "run_legacy.json"), []byte(data), 0o644); err != nil {
		t.Fatalf("write run json: %v", err)
	}

	runs, err := ListRuns(context.Background(), root, ListFilter{
		SessionID: "codex:019e5849-4460-7423-80c6-f39351b39992",
	})
	if err != nil {
		t.Fatalf("ListRuns: %v", err)
	}
	if len(runs) != 1 {
		t.Fatalf("expected 1 run, got %d", len(runs))
	}
	if runs[0].SessionID == nil || *runs[0].SessionID != "codex:019e5849-4460-7423-80c6-f39351b39992" {
		t.Fatalf("unexpected normalized session id: %#v", runs[0].SessionID)
	}
}
