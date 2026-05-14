"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { CommandIcon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useCommandPalette } from "@/store/command-palette";

export function CommandPalette() {
  const { open, setOpen, toggle } = useCommandPalette();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
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
        className="border-charcoal-700 bg-charcoal-900 max-w-xl p-0 shadow-2xl"
        showCloseButton={false}
      >
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
        >
          <DialogHeader className="border-charcoal-700 border-b px-5 py-4">
            <DialogTitle className="text-charcoal-200 flex items-center gap-2 font-mono text-sm font-medium">
              <CommandIcon className="size-3.5 text-amber-400" aria-hidden="true" />
              Command Palette
            </DialogTitle>
          </DialogHeader>

          <div className="px-5 py-8">
            <DialogDescription className="text-charcoal-400 text-center font-mono text-sm">
              No commands available yet — coming in Phase 1.
            </DialogDescription>
          </div>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
}
