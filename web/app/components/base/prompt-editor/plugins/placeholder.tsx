import { useTranslation } from 'react-i18next'

const Placeholder = ({
  value,
}: {
  value?: string
}) => {
  const { t } = useTranslation()

  return (
    <div className='absolute top-0 left-0 h-full w-full text-sm text-gray-300 select-none pointer-events-none leading-6'>
      {value || t('common.promptEditor.placeholder')}
    </div>
  )
}

export default Placeholder
