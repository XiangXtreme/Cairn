package cairn

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Run is the observer-side mirror of Cairn's worker run mapping file.
type Run struct {
	SchemaVersion int     `json:"schema_version"`
	RunID         string  `json:"run_id"`
	ProjectID     string  `json:"project_id"`
	IntentID      *string `json:"intent_id,omitempty"`
	Phase         string  `json:"phase"`
	WorkerName    string  `json:"worker_name"`
	AgentType     string  `json:"agent_type"`
	WorkspaceName string  `json:"workspace_name"`
	WorkspacePath string  `json:"workspace_path"`
	SessionID     *string `json:"session_id,omitempty"`
	Status        string  `json:"status"`
	StartedAt     string  `json:"started_at"`
	UpdatedAt     string  `json:"updated_at"`
	EndedAt       *string `json:"ended_at,omitempty"`
	ExitCode      *int    `json:"exit_code,omitempty"`
	TimedOut      bool    `json:"timed_out"`
	Cancelled     bool    `json:"cancelled"`
	CancelReason  *string `json:"cancel_reason,omitempty"`
	DurationMS    *int    `json:"duration_ms,omitempty"`
	StdoutPreview string  `json:"stdout_preview"`
	StderrPreview string  `json:"stderr_preview"`
	SourcePath    string  `json:"source_path"`
}

type ListFilter struct {
	ProjectID string
	IntentID  string
	SessionID string
	Limit     int
}

func RunsDirFromEnv() string {
	return os.Getenv("CAIRN_RUNS_DIR")
}

func ListRuns(ctx context.Context, root string, filter ListFilter) ([]Run, error) {
	if root == "" {
		return nil, nil
	}
	info, err := os.Stat(root)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, fmt.Errorf("stat Cairn runs dir: %w", err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("Cairn runs path is not a directory: %s", root)
	}

	var runs []Run
	err = filepath.WalkDir(root, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if !strings.EqualFold(filepath.Ext(path), ".json") {
			return nil
		}
		run, err := readRun(path)
		if err != nil {
			return err
		}
		if !matches(run, filter) {
			return nil
		}
		runs = append(runs, run)
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("listing Cairn runs: %w", err)
	}

	sort.Slice(runs, func(i, j int) bool {
		if runs[i].UpdatedAt == runs[j].UpdatedAt {
			return runs[i].RunID > runs[j].RunID
		}
		return runs[i].UpdatedAt > runs[j].UpdatedAt
	})
	if filter.Limit > 0 && len(runs) > filter.Limit {
		runs = runs[:filter.Limit]
	}
	return runs, nil
}

func readRun(path string) (Run, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Run{}, fmt.Errorf("read %s: %w", path, err)
	}
	var run Run
	if err := json.Unmarshal(data, &run); err != nil {
		return Run{}, fmt.Errorf("parse %s: %w", path, err)
	}
	run.SourcePath = path
	return run, nil
}

func matches(run Run, filter ListFilter) bool {
	if filter.ProjectID != "" && run.ProjectID != filter.ProjectID {
		return false
	}
	if filter.IntentID != "" {
		if run.IntentID == nil || *run.IntentID != filter.IntentID {
			return false
		}
	}
	if filter.SessionID != "" {
		if run.SessionID == nil || *run.SessionID != filter.SessionID {
			return false
		}
	}
	return true
}
