import { Download, FileDown } from 'lucide-react';
import { useI18n } from '../../../i18n';

interface ReportExportButtonsProps {
  onExportCsv: () => void;
  onExportPdf?: () => void;
  exportingCsv: boolean;
  exportingPdf?: boolean;
  disabled?: boolean;
}

/** CSV / PDF download pair shared by every report masthead. */
export default function ReportExportButtons({
  onExportCsv,
  onExportPdf,
  exportingCsv,
  exportingPdf = false,
  disabled = false,
}: ReportExportButtonsProps) {
  const { t } = useI18n();
  const busy = disabled || exportingCsv || exportingPdf;

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onExportCsv}
        disabled={busy}
        className="btn btn-secondary btn-sm"
      >
        <Download aria-hidden className="h-3.5 w-3.5" />
        {exportingCsv ? t.common.exporting : t.common.exportCsv}
      </button>
      {onExportPdf && (
        <button
          type="button"
          onClick={onExportPdf}
          disabled={busy}
          className="btn btn-secondary btn-sm"
        >
          <FileDown aria-hidden className="h-3.5 w-3.5" />
          {exportingPdf ? t.common.exportingPdf : t.common.exportPdf}
        </button>
      )}
    </div>
  );
}
