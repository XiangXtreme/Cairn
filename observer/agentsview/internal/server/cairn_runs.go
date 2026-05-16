package server

import (
	"net/http"
	"strconv"

	"github.com/wesm/agentsview/internal/cairn"
	"github.com/wesm/agentsview/internal/db"
)

type cairnRunsResponse struct {
	Configured bool        `json:"configured"`
	Root       string      `json:"root,omitempty"`
	Runs       []cairn.Run `json:"runs"`
}

func (s *Server) handleListCairnRuns(
	w http.ResponseWriter, r *http.Request,
) {
	root := cairn.RunsDirFromEnv()
	q := r.URL.Query()
	limit := db.DefaultSessionLimit
	if raw := q.Get("limit"); raw != "" {
		parsed, err := strconv.Atoi(raw)
		if err != nil || parsed < 0 {
			writeError(w, http.StatusBadRequest, "invalid limit")
			return
		}
		if parsed > db.MaxSessionLimit {
			parsed = db.MaxSessionLimit
		}
		limit = parsed
	}

	runs, err := cairn.ListRuns(r.Context(), root, cairn.ListFilter{
		ProjectID: q.Get("project_id"),
		IntentID:  q.Get("intent_id"),
		SessionID: q.Get("session_id"),
		Limit:     limit,
	})
	if err != nil {
		if handleContextError(w, err) {
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if runs == nil {
		runs = []cairn.Run{}
	}
	writeJSON(w, http.StatusOK, cairnRunsResponse{
		Configured: root != "",
		Root:       root,
		Runs:       runs,
	})
}
