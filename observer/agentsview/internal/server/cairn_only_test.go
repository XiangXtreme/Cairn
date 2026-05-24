package server

import "testing"

func TestCairnSessionIDVariantsIncludesClaudeSharedID(t *testing.T) {
	got := cairnSessionIDVariants("claudecode", "claude:345cdefd-1fc4-4caa-abb5-d337a721ee86")
	want := map[string]bool{
		"345cdefd-1fc4-4caa-abb5-d337a721ee86":        true,
		"claude:345cdefd-1fc4-4caa-abb5-d337a721ee86": true,
		"shared-345cdefd-1fc4-4caa-abb5-d337a721ee86": true,
	}
	if len(got) != len(want) {
		t.Fatalf("variants = %v, want %d variants", got, len(want))
	}
	for _, item := range got {
		if !want[item] {
			t.Fatalf("unexpected variant %q in %v", item, got)
		}
		delete(want, item)
	}
	for item := range want {
		t.Fatalf("missing variant %q in %v", item, got)
	}
}
