import { useState } from 'react';
import { PanelWrapper } from './PanelWrapper';
import { Camera, Image, FileImage, X } from 'lucide-react';

interface DetectionsGalleryProps {
  files: string[];
}

export function DetectionsGallery({ files }: DetectionsGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  if (files.length === 0) {
    return (
      <PanelWrapper 
        title="Captured Detections" 
        badge={<Camera className="w-3.5 h-3.5 text-muted-foreground" />}
      >
        <div className="flex flex-col items-center justify-center h-full gap-2 text-muted-foreground py-4">
          <Image className="w-8 h-8 opacity-30" />
          <span className="text-xs font-mono">NO CAPTURES YET</span>
        </div>
      </PanelWrapper>
    );
  }

  return (
    <>
      <PanelWrapper 
        title="Captured Detections" 
        badge={
          <div className="flex items-center gap-2">
            <Camera className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-mono text-primary font-bold">{files.length}</span>
          </div>
        }
      >
        <div className="h-full overflow-y-auto p-2 space-y-1 scrollbar-thin max-h-[200px]">
          {files.map((filename, index) => {
            const cleanName = filename.replace('.jpg', '').replace('_hires', '');
            const parts = cleanName.split('_');
            const label = parts[0]?.toUpperCase() || 'DETECTION';
            const date = parts[1] || '';
            const time = parts[2] || '';
            
            return (
              <div 
                key={filename}
                className="flex items-center gap-2 px-2 py-1.5 rounded bg-muted/30 border border-border/30 hover:border-primary/50 hover:bg-muted/50 transition-colors cursor-pointer group"
                onClick={() => setSelectedImage(filename)}
              >
                <FileImage className="w-3.5 h-3.5 text-primary/70 group-hover:text-primary" />
                <span className="text-[10px] font-mono font-bold text-primary flex-1 truncate">{label}</span>
                <span className="text-[9px] font-mono text-muted-foreground">{date}</span>
                <span className="text-[9px] font-mono text-muted-foreground">{time}</span>
              </div>
            );
          })}
        </div>
      </PanelWrapper>

      {/* Image Preview Modal */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setSelectedImage(null)}
        >
          <div 
            className="relative max-w-[90vw] max-h-[90vh] bg-space-black border border-primary/30 rounded-lg overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button 
              className="absolute top-2 right-2 z-10 p-1.5 bg-black/60 hover:bg-primary/20 rounded-full border border-primary/30 transition-colors"
              onClick={() => setSelectedImage(null)}
            >
              <X className="w-5 h-5 text-primary" />
            </button>
            
            {/* Image */}
            <img 
              src={`/detections/${selectedImage}`}
              alt={selectedImage}
              className="max-w-[90vw] max-h-[85vh] min-w-[400px] min-h-[400px] object-contain"
              style={{ imageRendering: 'auto' }}
            />
            
            {/* Filename Footer */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-3">
              <span className="text-sm font-mono text-primary">{selectedImage}</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
