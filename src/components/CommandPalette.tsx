"use client";

import { motion } from "framer-motion";
import { CommandIcon } from "lucide-react";
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { executeCommand } from "@/lib/commands";
import { useCommandPalette } from "@/store/command-palette";
import type { CommandSpec } from "../../types/plugin";

export function CommandPalette() {
  const { open, setOpen, toggle, commands } = useCommandPalette();

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="border-charcoal-700 bg-charcoal-900 max-w-xl gap-0 p-0 shadow-2xl"
        showCloseButton={false}
      >
        <DialogHeader className="border-charcoal-700 border-b px-5 py-3">
          <DialogTitle className="text-charcoal-200 flex items-center gap-2 font-mono text-sm font-medium">
            <CommandIcon className="size-3.5 text-amber-400" aria-hidden="true" />
            Command Palette
          </DialogTitle>
          <DialogDescription className="sr-only">
            Search and run commands contributed by the enabled modules.
          </DialogDescription>
        </DialogHeader>
        {/* The body is a child component so its query/highlight state resets
            each time the palette opens — Radix unmounts DialogContent while
            the dialog is closed. */}
        <CommandPaletteBody commands={commands} onClose={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}

interface CommandPaletteBodyProps {
  commands: CommandSpec[];
  onClose: () => void;
}

function CommandPaletteBody({ commands, onClose }: CommandPaletteBodyProps) {
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return commands;
    }
    return commands.filter(
      (command) =>
        command.title.toLowerCase().includes(needle) ||
        command.trigger.toLowerCase().includes(needle),
    );
  }, [commands, query]);

  function run(index: number) {
    const command = filtered[index];
    if (!command) {
      return;
    }
    executeCommand(command);
    onClose();
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight((current) => Math.min(current + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      run(highlight);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      <input
        ref={inputRef}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setHighlight(0);
        }}
        onKeyDown={handleInputKeyDown}
        placeholder="Search commands…"
        aria-label="Search commands"
        className="text-charcoal-100 placeholder:text-charcoal-400 w-full bg-transparent px-5 py-3 font-mono text-sm outline-none"
      />
      <div className="border-charcoal-700 max-h-80 overflow-y-auto border-t py-1">
        {filtered.length === 0 ? (
          <p className="text-charcoal-400 px-5 py-6 text-center font-mono text-sm">
            {commands.length === 0 ? "No commands registered yet." : "No matching commands."}
          </p>
        ) : (
          filtered.map((command, index) => (
            <button
              key={command.id}
              type="button"
              onClick={() => run(index)}
              onMouseEnter={() => setHighlight(index)}
              className={`flex w-full flex-col gap-0.5 px-5 py-2 text-left font-mono ${
                index === highlight ? "bg-charcoal-800" : ""
              }`}
            >
              <span className="text-charcoal-100 text-sm">{command.title}</span>
              {command.description ? (
                <span className="text-charcoal-400 text-xs">{command.description}</span>
              ) : null}
            </button>
          ))
        )}
      </div>
    </motion.div>
  );
}
